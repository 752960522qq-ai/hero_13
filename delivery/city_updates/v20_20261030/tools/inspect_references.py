import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
sources=[('S05',R.parent/'reference_models/city (1)(1).glb'),('S08',R.parent/'upload/city_street(1).glb'),('S02',R.parent/'upload/01-asian_buildings_set.glb')]
(R/'audit').mkdir(exist_ok=True);(R/'previews').mkdir(exist_ok=True)
for sid,path in sources:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];records=[]
 for o in bpy.context.scene.objects:
  if o.type=='MESH': obs=[o]
  elif o.name.startswith(('Object_','_gltf')):continue
  else:obs=[x for x in o.children_recursive if x.type=='MESH']
  if not obs:continue
  xyz=[x.matrix_world@Vector(v) for x in obs for v in x.bound_box]
  lo=[min(x[k] for x in xyz) for k in range(3)];hi=[max(x[k] for x in xyz) for k in range(3)]
  records.append({'name':o.name,'mesh':o.type=='MESH','parent':o.parent.name if o.parent else None,'children':len(obs),'bounds':[lo,hi],'size':[hi[i]-lo[i] for i in range(3)],'triangles':sum(sum(len(f.vertices)-2 for f in x.data.polygons) for x in obs)})
 (R/'audit'/f'{sid}_inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
 xyz=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box];lo=Vector([min(x[k] for x in xyz) for k in range(3)]);hi=Vector([max(x[k] for x in xyz) for k in range(3)]);c=(lo+hi)/2;s=max(hi-lo)
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=10;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=8;sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.use_simplify=True;sc.cycles.texture_limit_render='2048';sc.world=bpy.data.worlds.new('Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.7,.8,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.8
 ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.8;ld.angle=.15;ob=bpy.data.objects.new('Sun',ld);sc.collection.objects.link(ob);ob.rotation_euler=(.5,-.35,-.5)
 cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);sc.collection.objects.link(cam);cd.type='ORTHO';cd.ortho_scale=s*1.2;cd.clip_end=s*10;cam.location=c+Vector((.8,-1.2,1.1))*s;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();sc.camera=cam;sc.render.filepath=str(R/'previews'/f'{sid}_reference.png');bpy.ops.render.render(write_still=True)
 if sid=='S05':
  cam.location=c+Vector((0,0,s*2));cam.rotation_euler=(0,0,0);cd.ortho_scale=s*1.05;sc.render.filepath=str(R/'previews'/f'{sid}_road_plan.png');bpy.ops.render.render(write_still=True)
 print('INSPECTED',sid,len(records),list(hi-lo),flush=True)
