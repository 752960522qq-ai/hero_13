"""Render the real assembled arcade row without hiding city objects."""
from pathlib import Path
import argparse,json,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--only',nargs='*');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;row=json.loads(a.plan.read_text())['connected_arcades'];origin=np.array(row['front_origin']);u=np.array(row['u']);v=np.array(row['v']);z=row['foundation_top_m'];xmin,xmax=row['local_x_range']
def pt(x,y,h):return [*(origin+u*x+v*y),z+h]
sc.render.engine='CYCLES';sc.cycles.samples=14;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.035
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85;sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.5;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
cam=sc.camera;cam.data.clip_start=.03;cam.data.clip_end=30000;cam.data.dof.use_dof=False
views=[('01_arcade_street_context',pt(-36,-37,62),pt(0,3,4),78,(1900,1350),'ORTHO'),('02_connected_frontage',pt(0,-25,7.5),pt(0,1,5.2),14,(2100,1100),'PERSP'),('03_covered_walkthrough',pt(xmin+1.5,-1.6,1.7),pt(xmax-3,-1.6,1.8),22,(1900,1250),'PERSP'),('04_arcade_corner',pt(35,-31,55),pt(0,3,4),75,(1900,1350),'ORTHO')]
manifest=[]
for name,loc,target,size,res,kind in views:
    manifest.append({'name':name,'camera':loc,'target':target,'projection':kind,'size_or_lens':size,'hidden_objects':0})
    if a.only and name not in a.only:continue
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=kind
    if kind=='ORTHO':cam.data.ortho_scale=size
    else:cam.data.lens=size
    sc.render.resolution_x,sc.render.resolution_y=res;sc.render.filepath=str((a.out/(name+'.png')).resolve());print('ARCADE_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('ARCADE_RENDER_DONE',name,flush=True)
(a.out/'connected_arcade_cameras.json').write_text(json.dumps(manifest,indent=2))
