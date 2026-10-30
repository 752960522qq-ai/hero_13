from pathlib import Path
import sys,json,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'))
import bpy,numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [];before='before' in args
if before:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 for d in [4,8,9,10]:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
else:bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v21.blend'))
bpy.context.view_layer.update();sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=14;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=8;sc.render.use_simplify=True;sc.cycles.texture_limit_render='1024';sc.world=bpy.data.worlds.new('V21_Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.73,.81,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.8
ld=bpy.data.lights.new('V21_Sun','SUN');ld.energy=2.7;ld.angle=.12;o=bpy.data.objects.new('V21_Sun',ld);sc.collection.objects.link(o);o.rotation_euler=(.5,-.3,-.5);sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.2
views=[('01_newtown_north',(1065,585,275),(735,820,28),350,(1800,1400)),('02_newtown_east',(1085,585,240),(853,754,30),290,(1800,1400)),('03_west_courts',(-1290,-1030,215),(-1140,-805,12),320,(1800,1400)),('04_west_street',(-936,-1001,165),(-772,-797,12),250,(1800,1400)),('05_newtown_plan',(780,710,1300),(780,710,18),550,(1800,1600)),('06_south_mixed',(1040,290,200),(828,500,22),270,(1800,1400))]
if before:views=views[:4]
if 'quick' in args:views=views[:2];sc.cycles.samples=8
out=R/'renders';out.mkdir(exist_ok=True);sites=json.load(open(R/'model/site_levels.json')) if not before else [];projections=[]
for name,loc,target,scale,res in views:
 cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=scale;cd.clip_start=.05;cd.clip_end=10000;sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.resolution_percentage=100;sc.render.filepath=str(out/(name+('_before' if before else '')+'.png'));bpy.ops.render.render(write_still=True)
 anchors=[]
 for s in sites:
  pt=Vector((*s['center'],s['floor']+s['height']+.6));v=world_to_camera_view(sc,cam,pt)
  if 0<v.x<1 and 0<v.y<1 and v.z>0:anchors.append(dict(instance_id=s['instance_id'],asset_id=s['asset_id'],x=float(v.x*res[0]),y=float((1-v.y)*res[1]),group=s['group']))
 projections.append(dict(file=name+'.png',width=res[0],height=res[1],anchors=anchors));print('RENDERED',name,before,flush=True)
if not before:(out/'projections.json').write_text(json.dumps(projections,ensure_ascii=False,indent=2))
