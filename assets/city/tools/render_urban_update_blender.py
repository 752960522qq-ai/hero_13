"""Render inspection views of the complete, unhidden urban scene."""
from pathlib import Path
import argparse,json,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--update',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));bpy.context.view_layer.update()
sc=bpy.context.scene;records=json.loads(args.update.read_text())['instances']
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.03
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.35
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
camera=sc.camera;camera.data.type='ORTHO';camera.data.clip_start=.1;camera.data.clip_end=30000;camera.data.dof.use_dof=False
mid=np.mean(np.array([r['center'] for r in records]),axis=0);ground=float(np.mean([r['foundation_top_m'] for r in records]))
views=[
    ('01_cbd_aerial',np.array([325,85,1450]),np.array([140,960,28]),1350,(1850,1450)),
    ('02_cbd_streets',np.array([390,595,650]),np.array([115,980,30]),760,(1800,1400)),
    ('03_oldtown_two_apartments',np.array([mid[0]+74,mid[1]+100,ground+90]),np.array([mid[0],mid[1]+3,ground+10]),155,(1800,1400)),
    ('04_oldtown_apartment_2',np.array([records[0]['center'][0]+24,records[0]['center'][1]+55,records[0]['foundation_top_m']+48]),np.array([*records[0]['center'],records[0]['foundation_top_m']+10]),52,(1400,1400)),
    ('05_oldtown_apartment_3',np.array([records[1]['center'][0]+23,records[1]['center'][1]+52,records[1]['foundation_top_m']+46]),np.array([*records[1]['center'],records[1]['foundation_top_m']+10]),51,(1400,1400)),
]
manifest=[]
for name,loc,target,scale,size in views:
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    sc.render.resolution_x,sc.render.resolution_y=size;sc.render.filepath=str((args.out/(name+'.png')).resolve())
    manifest.append({'name':name,'camera':loc.tolist(),'target':target.tolist(),'ortho_scale':scale,'hidden_objects':0})
    print('URBAN_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('URBAN_RENDER_DONE',name,flush=True)
(args.out/'urban_preview_cameras.json').write_text(json.dumps(manifest,indent=2))
