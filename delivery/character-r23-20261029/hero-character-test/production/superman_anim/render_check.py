import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'superman_animated.blend'));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');sc=bpy.context.scene
for tr in t.animation_data.nla_tracks:tr.mute=True
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='TEXTURE';sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world=bpy.data.worlds.new('World');sc.world.color=(.65,.65,.65);cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));sc.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.ortho_scale=2.0;center=Vector((0,0,.85));cam.location=center+Vector((2.5,-4,1));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();sc.camera=cam;sc.render.resolution_x=750;sc.render.resolution_y=850;sc.render.resolution_percentage=100
for label in ['Idle','Walk','Run']:
 a=bpy.data.actions.get(label);t.animation_data.action=a;f=(a.frame_range.x+a.frame_range.y)*.5;sc.frame_set(int(f),subframe=f-int(f));sc.render.filepath=str(P/(label+'.png'));bpy.ops.render.render(write_still=True)
