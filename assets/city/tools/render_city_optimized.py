"""Actual Blender previews of the revised road/sidewalk model."""
from pathlib import Path
from mathutils import Vector
import bpy,json,argparse,sys
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--quick',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
args.out.mkdir(parents=True,exist_ok=True);plan=json.loads(args.plan.read_text())
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16 if not args.quick else 8;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.03
sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.35
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
cam=sc.camera;cam.data.clip_start=.1;cam.data.clip_end=30000
candidate=min((n for n in plan['nodes'] if len(n['edges'])>=4),key=lambda n:(n['xy'][0]+700)**2+(n['xy'][1]-720)**2)
x,y=candidate['xy'];z=candidate['z']
views=[
('01_junction_sidewalks',(x+150,y-180,z+190),(x,y,z),330,(1680,1400)),
('02_hills_sidewalks',(-1250,750,220),(-900,1330,65),None,(1920,1440)),
('03_bridge_junction',(650,-1450,360),(150,-790,25),None,(1920,1440)),
('04_road_network_top',(0,0,8000),(0,0,0),4140,(2048,2048))]
if args.quick:views=views[:1]
for name,location,target,ortho,size in views:
    cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP';cam.data.ortho_scale=ortho or 100;cam.data.lens=43
    sc.render.resolution_x,sc.render.resolution_y=size
    if args.quick:sc.render.resolution_percentage=65
    sc.render.filepath=str((args.out/(name+'.png')).resolve());print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
print('OPTIMIZED_PREVIEWS_COMPLETE',flush=True)
