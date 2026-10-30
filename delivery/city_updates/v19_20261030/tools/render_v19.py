import sys,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'))
import bpy,numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [];before='before' in args
bpy.ops.wm.read_factory_settings(use_empty=True) if before else bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'))
context=[1,2,3,5,6,7]
if before:context=[4,8,9,14]+context
for d in context:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.context.view_layer.update();sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=8;sc.render.use_simplify=True;sc.cycles.texture_limit_render='1024';sc.world=bpy.data.worlds.new('Daylight');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.64,.72,.81,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85
sun=bpy.data.lights.new('Sun','SUN');sun.energy=2.5;sun.angle=.12;o=bpy.data.objects.new('Sun',sun);sc.collection.objects.link(o);o.rotation_euler=(.48,-.35,-.45);sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.25
mat=bpy.data.materials.new('Preview_Water');mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.10,.25,.32,1);bs.inputs['Roughness'].default_value=.65;bpy.ops.mesh.primitive_plane_add(size=10000,location=(0,0,-.2));bpy.context.object.data.materials.append(mat)
views=[('01_newtown_courts',(1100,180,355),(780,508,20),400,(1900,1400)),('02_west_court_close',(528,340,145),(717,492,20),230,(1900,1400)),('03_mixed_promonade',(980,620,260),(765,798,28),310,(1900,1400)),('04_west_garden',(-1280,-1130,175),(-1102,-960,15),240,(1900,1400)),('05_industrial_court',(1100,-1130,200),(902,-864,17),300,(1900,1400)),('06_main_island',(1800,-1850,2150),(80,630,30),2350,(2000,1450))]
if before:views=[views[0],views[3],views[4]]
out=R/'renders';out.mkdir(exist_ok=True);sites=json.load(open(R/'model/site_levels.json'));projections=[]
for name,loc,target,scale,res in views:
 c=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,c);sc.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=scale;c.clip_start=.05;c.clip_end=20000;sc.camera=o;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.resolution_percentage=100;sc.render.filepath=str(out/(name+('_before' if before else '')+'.png'));bpy.ops.render.render(write_still=True)
 if not before:
  anchors=[]
  for rec in sites:
   pt=Vector((*rec['center'],rec['floor']+rec['height']+.5));v=world_to_camera_view(sc,o,pt)
   if 0<v.x<1 and 0<v.y<1 and v.z>0:anchors.append({'instance_id':rec['instance_id'],'asset_id':rec['asset_id'],'x':float(v.x*res[0]),'y':float((1-v.y)*res[1]),'group':rec['group']})
  projections.append({'file':name+'.png','width':res[0],'height':res[1],'anchors':anchors})
 print('RENDER_DONE',name,before,flush=True)
if not before:(R/'renders/projections.json').write_text(json.dumps(projections,ensure_ascii=False,indent=2))
