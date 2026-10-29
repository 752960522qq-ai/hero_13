import bpy,json,math
from mathutils import Vector
from pathlib import Path
out=Path('/workspace/hero-character-test/production');report={}
for label,p in [('superman','/workspace/attachments/ff4adad4-1835-458d-abce-de913ca05dd1/superman.glb'),('double','/workspace/attachments/8a7efad6-6849-42a3-830a-eb33a604c716/double stars have head.glb')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=p)
 vs=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices];lo=[min(v[i] for v in vs)for i in range(3)];hi=[max(v[i]for v in vs)for i in range(3)]
 r={'bounds':[lo,hi],'meshes':[(o.name,len(o.data.vertices))for o in bpy.data.objects if o.type=='MESH']}
 t=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
 if t:r['bones']={b.name:{'head':list(t.matrix_world@b.head_local),'tail':list(t.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None}for b in t.data.bones}
 report[label]=r
 for ob in list(bpy.data.objects):
  if ob.type not in ['MESH','ARMATURE']:bpy.data.objects.remove(ob,do_unlink=True)
 sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='TEXTURE';sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world=bpy.data.worlds.new('World');sc.world.color=(.6,.6,.6)
 # initial camera front along -Y
 center=Vector([(lo[i]+hi[i])/2 for i in range(3)]);size=max(hi[i]-lo[i]for i in range(3));cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));sc.collection.objects.link(cam);cam.location=center+Vector((0,-size*2,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size*1.15;sc.camera=cam;sc.render.resolution_x=850;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.filepath=str(out/(label+'_original.png'));bpy.ops.render.render(write_still=True)
(out/'inspection.json').write_text(json.dumps(report,indent=2))
