import bpy
from mathutils import Vector
from pathlib import Path
OUT=Path(__file__).resolve().parent.parent/'qa'/'beige-feet';OUT.mkdir(exist_ok=True)
for pose in ['Idle','Walk','Run']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=f'/tmp/beige_{pose}_body.glb');bpy.ops.import_scene.gltf(filepath=f'/tmp/beige_{pose}_shoe.glb')
 pts=[o.matrix_world@Vector(p) for o in bpy.context.scene.objects if o.type=='MESH' and ('BeigeHeel' in o.name or 'BeigeFootSkin' in o.name) for p in o.bound_box];center=sum(pts,Vector())/len(pts);center.z+=.045
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.use_denoising=False;s.render.resolution_x=600;s.render.resolution_y=650;s.render.resolution_percentage=100;s.world.color=(.5,.5,.5)
 for loc,power,size in [((1,-2,3),120,2),((-2,1,2),80,2)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.size=size
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001));m=bpy.data.materials.new('Floor');m.diffuse_color=(.25,.25,.25,1);bpy.context.object.data.materials.append(m)
 bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.80
 for view,delta in [('front',(.6,-1,.48)),('side',(1,0,.15))]:
  cam.location=center+Vector(delta);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(OUT/f'{pose}_{view}.png');bpy.ops.render.render(write_still=True)
