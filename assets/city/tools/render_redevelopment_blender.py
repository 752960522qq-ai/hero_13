"""Render complete unhidden city views for the redevelopment review."""
from pathlib import Path
import argparse,json,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));bpy.context.view_layer.update();sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.03
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.35;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
camera=sc.camera;camera.data.type='ORTHO';camera.data.clip_start=.1;camera.data.clip_end=30000;camera.data.dof.use_dof=False
views=[
 ('01_cbd_blocks',(325,85,1450),(140,960,28),1350,(1850,1450)),
 ('02_cbd_podiums',(390,595,650),(115,980,30),760,(1800,1400)),
 ('03_oldtown_residential',(35,360,105),(-39,263,20),175,(1800,1400)),
 ('04_repaired_junction',(18.1765,270.8412,320),(18.1765,270.8412,10),110,(1400,1400)),
 ('05_east_port',(1640,-890,520),(1160,-510,10),950,(1800,1400)),
 ('06_west_lake',(-1700,-1300,520),(-980,-630,25),1050,(1800,1400)),
 ('07_bridge_junction',(650,-1450,360),(150,-790,25),1020,(1800,1400)),
 ('08_port_yard_access',(1095,-775,195),(950,-615,12),240,(1800,1400)),
]
manifest=[]
for name,loc,target,scale,size in views:
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    sc.render.resolution_x,sc.render.resolution_y=size;sc.render.filepath=str((args.out/(name+'.png')).resolve())
    manifest.append({'name':name,'camera':loc,'target':target,'ortho_scale':scale,'hidden_objects':0})
    print('REDEVELOPMENT_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('REDEVELOPMENT_RENDER_DONE',name,flush=True)
(args.out/'redevelopment_preview_cameras.json').write_text(json.dumps(manifest,indent=2))
