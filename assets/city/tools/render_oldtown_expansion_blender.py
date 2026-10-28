"""Render the open frontage, side-stretched corner shop and new apartment."""
from pathlib import Path
import argparse,json,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--only',nargs='*');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;p=json.loads(a.plan.read_text());row=p['connected_arcades'];o=np.array(row['front_origin']);u=np.array(row['u']);v=np.array(row['v']);z=row['foundation_top_m'];x=row['body_max_x'];apt=p['oldtown_expansion']['apartment'];center=np.array(apt['center']);az=apt['foundation_top_m']
def pt(x,y,h):return [*(o+u*x+v*y),z+h]
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.035;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85;sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.45;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
cam=sc.camera;cam.data.clip_start=.05;cam.data.clip_end=30000;cam.data.dof.use_dof=False
views=[('01_extended_oldtown_street',pt(-55,-65,110),pt(0,4,4),158,(2100,1350),'ORTHO'),('02_corner_shop_side',pt(x+15,-17,12),pt(x-4,3,4.8),28,(1900,1400),'PERSP'),('03_apartment11_context',[center[0]-24,center[1]-35,az+46],[center[0],center[1],az+5],80,(1900,1350),'ORTHO'),('04_city_overview',(250,-1700,5200),(0,0,0),4650,(2100,1900),'ORTHO')]
manifest=[]
for name,loc,target,size,res,kind in views:
    manifest.append({'name':name,'camera':loc,'target':target,'projection':kind,'size_or_lens':size,'hidden_objects':0})
    if a.only and name not in a.only:continue
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=kind
    if kind=='ORTHO':cam.data.ortho_scale=size
    else:cam.data.lens=size
    sc.render.resolution_x,sc.render.resolution_y=res;sc.render.filepath=str((a.out/(name+'.png')).resolve());print('EXPANSION_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('EXPANSION_RENDER_DONE',name,flush=True)
(a.out/'oldtown_expansion_cameras.json').write_text(json.dumps(manifest,indent=2))
