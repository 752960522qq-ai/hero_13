"""Inspect the actual posed visible meshes in Blender, including module masks."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'qa/junction-closeups'
def cv(v):return (v[0],-v[2],v[1])
reports=[]
for pose in ['Idle','Run']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 data=json.loads((OUT/f'{pose}_geometry.json').read_text());report={'pose':pose,'meshes':[]}
 for item in data:
  v=item['positions'];verts=[cv(v[i:i+3]) for i in range(0,len(v),3)];idx=item['indices'];faces=[idx[i:i+3] for i in range(0,len(idx),3)]
  mesh=bpy.data.meshes.new(item['name']);mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new(item['name'],mesh);bpy.context.collection.objects.link(obj)
  mat=bpy.data.materials.new(item['name']);mat.diffuse_color=(*item['color'],1);obj.data.materials.append(mat)
  for p in mesh.polygons:p.use_smooth=True
  report['meshes'].append({'name':obj.name,'vertices':len(verts),'triangles':len(faces),'zeroAreaFaces':sum(p.area<1e-12 for p in mesh.polygons)})
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.background_type='WORLD';scene.world.color=(.6,.6,.6)
 scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
 bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.clip_start=.001
 for label in ['neck_front','neck_back','wrist_l','wrist_r','ankle_l','ankle_r']:
  c=json.loads((OUT/f'{pose}_{label}_camera.json').read_text());cam.location=cv(c['position']);target=Vector(cv(c['target']));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.angle=math.radians(c['fov']);scene.render.filepath=str(OUT/f'Blender_{pose}_{label}.png');bpy.ops.render.render(write_still=True)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'Blender_{pose}_assembled.blend'));reports.append(report)
(OUT/'blender_geometry_report.json').write_text(json.dumps(reports,indent=2));print('Blender posed assembly checks and closeups complete')
