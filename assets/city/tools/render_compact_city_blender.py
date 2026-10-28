"""Render actual reconstruction geometry, without hiding model defects or adding AI imagery."""
import argparse,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--only');ap.add_argument('--samples',type=int,default=24)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;p=json.loads(a.plan.read_text());a.out.mkdir(parents=True,exist_ok=True)
sc.render.engine='CYCLES';sc.cycles.samples=a.samples;sc.cycles.use_denoising=True;sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100;sc.render.film_transparent=False
sc.world.use_nodes=True;bg=sc.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.55,.68,.80,1);bg.inputs['Strength'].default_value=.75
sun=bpy.data.lights.new('Preview_Sun','SUN');sun.energy=3.;sun.angle=.16;o=bpy.data.objects.new('Preview_Sun',sun);sc.collection.objects.link(o);o.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-28))
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.40
row=[r for r in p['real_buildings'] if 'Connected_' in r['instance_name']];floor=np.mean([r['floor'] for r in row]);lower=next(e for e in p['edges'] if e['name']=='MAIN_EW_650' and min(np.array(e['points'])[:,0])<=860<=max(np.array(e['points'])[:,0]));co=np.array(lower['points']);zlow=float(np.interp(860,co[:,0],co[:,2]))
cameras=[
 ('01_city_overview',(0,-2200,4500),(0,0,10),3900,(2200,2000)),
 ('02_cbd_interchange',(-520,500,420),(40,1020,22),1200,(1900,1400)),
 ('03_oldtown_frontage',(235,155,floor+72),(280,255,floor+7),185,(2100,1400)),
 ('04_east_flyover',(1120,340,260),(860,650,18),650,(1900,1400)),
 ('05_underpass',(785,650,zlow+2.1),(915,650,zlow+2.1),None,(1800,1200))]
records=[]
for name,loc,target,ortho,res in cameras:
    if a.only and name not in a.only.split(','):continue
    data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.clip_end=15000;data.clip_start=.05
    if ortho:data.type='ORTHO';data.ortho_scale=ortho
    else:data.type='PERSP';data.lens=38
    sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str((a.out/(name+'.png')).resolve());bpy.ops.render.render(write_still=True);records.append({'name':name,'location':loc,'target':target,'ortho_scale':ortho,'resolution':res});print('PREVIEW_SAVED',name,flush=True)
(a.out/'compact_render_cameras.json').write_text(json.dumps(records,indent=2))
