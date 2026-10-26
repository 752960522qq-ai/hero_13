"""Select unobstructed CBD camera views and render the actual complete scene."""
from pathlib import Path
import argparse,json,math,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--placements',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));bpy.context.view_layer.update();sc=bpy.context.scene;report=json.loads(args.placements.read_text());records=report['instances']
occluders=[]
for o in sc.objects:
    if o.type=='MESH' and o.get('is_placeholder'):
        q=np.array([o.matrix_world@Vector(p) for p in o.bound_box]);occluders.append([q.min(0),q.max(0)])
boxes=np.array(occluders)
def model_points(r):
    a=r['angle'];front=np.array([math.sin(a),-math.cos(a)]);across=np.array([math.cos(a),math.sin(a)]);sx,sy,h=r['placed_dimensions_m'];center=np.array(r['center']);points=[]
    for z in [.12,.3,.55,.8,.94]:
        for side in [-.28,0,.28]:
            xy=center+front*sy*.35+across*sx*side;points.append([*xy,r['building_base_m']+h*z])
    return np.array(points)
points=[model_points(r) for r in records]
def visible(cam,targets,exclude):
    other=[]
    for i,r in enumerate(records):
        if i in exclude:continue
        o=next(o for o in sc.objects if o.name.startswith(r['instance_name']+'_Source_Mesh'))
        q=np.array([o.matrix_world@Vector(p) for p in o.bound_box]);other.append([q.min(0),q.max(0)])
    blocks=np.concatenate([boxes,np.array(other)]) if other else boxes
    ray=targets[:,None,:]-cam[None,None,:];safe=np.where(np.abs(ray)<1e-9,1e-9,ray)
    t0=(blocks[None,:,0,:]-cam)/safe;t1=(blocks[None,:,1,:]-cam)/safe
    near=np.minimum(t0,t1).max(2);far=np.maximum(t0,t1).min(2);hit=(np.maximum(near,0)<np.minimum(far,1))
    return float((~hit.any(1)).mean())
def choose(indices):
    center=np.mean([records[i]['center'] for i in indices],axis=0);z0=float(np.mean([records[i]['building_base_m'] for i in indices]));target=np.array([*center,z0+(32 if len(indices)>1 else records[indices[0]]['target_height_m']*.42)])
    angle=float(np.mean([records[i]['angle'] for i in indices]));front=np.array([math.sin(angle),-math.cos(angle)]);bearing=math.atan2(front[1],front[0]);best=None
    for dist in [65,90,120,155,190,240]:
        for degrees in [0,-12,12,-25,25,-40,40,-55,55]:
            phi=bearing+math.radians(degrees)
            for rise in [65,85,110,140,175,205]:
                cam=np.array([center[0]+dist*math.cos(phi),center[1]+dist*math.sin(phi),z0+rise]);scores=[visible(cam,points[i],{i}) for i in indices]
                score=min(scores)*100+np.mean(scores)*10-abs(degrees)*.02-abs(math.degrees(math.atan2(rise-30,dist))-29)*.12
                if best is None or score>best[0]:best=(score,cam,target,scores)
    return best
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.025;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.35;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
camera=sc.camera;camera.data.clip_start=.1;camera.data.clip_end=30000;camera.data.dof.use_dof=False;manifest=[]
for name,indices,ortho,size in [('01_cbd_two_buildings',[0,1],180,(1900,1450)),('02_modern_glass_building',[0],108,(1600,1600)),('03_office_building',[1],91,(1600,1500))]:
    score,loc,target,visibility=choose(indices);camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=ortho
    sc.render.resolution_x,sc.render.resolution_y=size;sc.render.filepath=str((args.out/(name+'.png')).resolve())
    manifest.append({'name':name,'camera':loc.tolist(),'target':target.tolist(),'visibility_fractions':visibility,'ortho_scale':ortho,'hidden_objects':0});print('CBD_RENDER_START',json.dumps(manifest[-1]),flush=True)
    if name=='01_cbd_two_buildings':bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()),compress=True)
    bpy.ops.render.render(write_still=True);print('CBD_RENDER_DONE',name,flush=True)
(args.out/'cbd_preview_cameras.json').write_text(json.dumps(manifest,indent=2));print('CBD_PREVIEWS_COMPLETE',flush=True)
