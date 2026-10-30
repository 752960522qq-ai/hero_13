import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'));sc=bpy.context.scene
c=bpy.data.cameras.new('Diag');cam=bpy.data.objects.new('Diag',c);sc.collection.objects.link(cam);cam.location=(528,340,145);target=Vector((717,492,20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=230;sc.camera=cam;sc.render.resolution_x=1900;sc.render.resolution_y=1400;bpy.context.view_layer.update()
frame=c.view_frame(scene=sc);print('frame',[v[:] for v in frame],flush=True)
for px,py in [(1377,957),(1370,975),(1464,387),(1634,449),(1268,482)]:
 x=(px/1900-.5)*230;y=(.5-py/1400)*230*1400/1900;start=cam.matrix_world@Vector((x,y,0));direction=cam.matrix_world.to_3x3()@Vector((0,0,-1));hit,point,norm,index,obj,M=sc.ray_cast(bpy.context.evaluated_depsgraph_get(),start,direction)
 
 if not hit:
  for zz in [0,8,12,16,20]:
   q=start+direction*((zz-start.z)/direction.z);print('MISS_PLANE',zz,q[:],flush=True)
 print('RAY',px,py,hit,point[:],obj.name if obj else None,dict(obj.items()) if obj else None,'face',index,'normal',norm[:],flush=True)
 if obj:
  print('MATS',[(mat.name if mat else None) for mat in obj.data.materials],flush=True)
