"""Render the corrected right corner, flush frontage and metric references."""
from pathlib import Path
import argparse,json,math,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser()
for key in ['blend','plan','out']:ap.add_argument('--'+key,type=Path,required=True)
ap.add_argument('--deps',type=Path);ap.add_argument('--only',nargs='*')
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;p=json.loads(a.plan.read_text());row=p['connected_arcades'];O=np.array(row['front_origin']);U=np.array(row['u']);V=np.array(row['v']);Z=row['foundation_top_m'];X=row['body_max_x']
def pt(x,y,z):return [*(O+U*x+V*y),Z+z]
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.cycles.use_adaptive_sampling=True;sc.cycles.adaptive_threshold=.035;sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85;sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.45;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.resolution_percentage=100
cam=sc.camera;cam.data.clip_start=.05;cam.data.clip_end=30000;cam.data.dof.use_dof=False
views=[('01_sidewalk_frontage',pt(0,-105,76),pt(0,1,4.5),148,(2100,1250),'ORTHO'),('02_right_corner',pt(X+15,-17,12),pt(X-4,3,4.8),29,(1900,1400),'PERSP'),('03_scale_reference',pt(-8,-34,28),pt(-8,-3,4),58,(1900,1350),'ORTHO')]
references=[]
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.5;return m
blue=mat('QA_car_blue',(.04,.22,.47));dark=mat('QA_rubber',(.025,.03,.035));glass=mat('QA_glass',(.06,.10,.14));orange=mat('QA_person',(.95,.31,.04))
def box(name,loc,scale,material):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=scale;o.rotation_euler[2]=math.atan2(U[1],U[0]);o.data.materials.append(material);references.append(o);return o
if a.deps:
 sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parent));from city_surface_sampling import HeightField
 roads=HeightField([o for o in sc.objects if o.type=='MESH' and o.name.startswith(('MAIN_Road_Modular_Repaired_Cell_','Continuous_Pavement_Repaired_Cell_'))]);walk=HeightField([o for o in sc.objects if o.type=='MESH' and o.name.startswith(('MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_'))])
 human=O-U*12-V*1.65;hz=walk.height(human);car=O-U*10-V*9.4;cz=roads.height(car);assert hz is not None and cz is not None
 # Human extends from the pavement to 1.75m; car bounds are 4.5 x 1.8 x 1.5m.
 box('QA_Car_4.5m_1.8m',(*car,cz+.53),(4.5,1.8,.55),blue);box('QA_Car_Cabin',(*(car-U*.16),cz+1.08),(2.55,1.56,.84),glass)
 for dx in [-1.38,1.38]:
  for dy in [-.77,.77]:
   xy=car+U*dx+V*dy;bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=(*xy,cz+.30));o=bpy.context.object;o.scale=(.30,.13,.30);o.rotation_euler[2]=math.atan2(U[1],U[0]);o.data.materials.append(dark);references.append(o)
 box('QA_Human_Legs',(*human,hz+.43),(.34,.22,.86),dark);box('QA_Human_Torso',(*human,hz+1.14),(.44,.26,.56),orange)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.165,location=(*human,hz+1.585));o=bpy.context.object;o.data.materials.append(orange);references.append(o)
 for side in [-1,1]:box('QA_Human_Arm',(*(human+U*side*.29),hz+1.13),(.13,.15,.58),orange)
manifest=[]
for name,loc,target,size,res,kind in views:
 manifest.append({'image':name+'.png','camera':loc,'target':target,'scale_reference_objects':name=='03_scale_reference','human_height_m':1.75,'car_size_m':[4.5,1.8,1.5]})
 if a.only and name not in a.only:continue
 for o in references:o.hide_render=name!='03_scale_reference'
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=kind
 if kind=='ORTHO':cam.data.ortho_scale=size
 else:cam.data.lens=size
 sc.render.resolution_x,sc.render.resolution_y=res;sc.render.filepath=str((a.out/(name+'.png')).resolve());print('ALIGNED_RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('ALIGNED_RENDER_DONE',name,flush=True)
(a.out/'aligned_frontage_cameras.json').write_text(json.dumps(manifest,indent=2))
