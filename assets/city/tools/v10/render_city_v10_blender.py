"""Actual Blender renders of the 3.25 km², 640-building reconstruction."""
import argparse,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--only');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;p=json.loads(a.plan.read_text());sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
sc.world.use_nodes=True;bg=sc.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.55,.68,.8,1);bg.inputs['Strength'].default_value=.8
sun=bpy.data.lights.new('City_v10_Sun','SUN');sun.energy=3.;sun.angle=.16;o=bpy.data.objects.new(sun.name,sun);sc.collection.objects.link(o);o.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-28));sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
e=next(e for e in p['edges'] if e['name']=='MAIN_EW_650' and np.min(np.array(e['points'])[:,0])<=620<=np.max(np.array(e['points'])[:,0]));co=np.array(e['points']);floor=float(np.interp(620,co[:,0],co[:,2]))
views=[('01_city_overview',(0,-2350,3800),(-100,0,8),3350,(2100,1900)),('02_oldtown_blocks',(60,-160,520),(150,260,14),1100,(1800,1350)),('03_original_frontage',(155,145,110),(278,244,18),215,(1800,1250)),('04_cbd_diamond',(-430,630,420),(30,925,22),1080,(1800,1300)),('05_east_flyover',(900,440,260),(620,650,17),630,(1800,1200)),('06_underpass',(545,650,floor+2.1),(695,650,floor+2.1),None,(1600,1000))]
for name,loc,target,ortho,res in views:
 if a.only and name not in a.only.split(','):continue
 data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.clip_end=12000;data.clip_start=.06
 if ortho:data.type='ORTHO';data.ortho_scale=ortho
 else:data.type='PERSP';data.lens=35
 sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str((a.out/(name+'.png')).resolve());bpy.ops.render.render(write_still=True);print('V10_RENDER_SAVED',name,flush=True)
(a.out/'render_cameras.json').write_text(json.dumps([{'name':n,'location':l,'target':t,'ortho_scale':s,'resolution':r} for n,l,t,s,r in views],indent=2))
