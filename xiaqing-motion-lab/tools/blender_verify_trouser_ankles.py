"""Check actual browser-posed calf surfaces and render them in Blender."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'qa/ankle-alignment';reports=[]
def cv(p):return Vector((p[0],-p[2],p[1]))
for pose in ['Idle','Walk','Run']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data=json.loads((OUT/f'{pose}_posed.json').read_text());geometry={}
    for item in data:
        p=item['positions'];v=[cv(p[i:i+3]) for i in range(0,len(p),3)];idx=item['indices'];f=[idx[i:i+3] for i in range(0,len(idx),3)]
        mesh=bpy.data.meshes.new(item['name']);mesh.from_pydata(v,[],f);mesh.update();obj=bpy.data.objects.new(item['name'],mesh);bpy.context.collection.objects.link(obj)
        mat=bpy.data.materials.new(item['name']);mat.diffuse_color=(*item['color'],1);obj.data.materials.append(mat)
        for face in mesh.polygons:face.use_smooth=True
        geometry[item['name']]=(item,v,f)
    for side in ['l','r']:
        _,v,f=geometry['Suit_calf_'+side];tree=BVHTree.FromPolygons(v,f)
        body,points,_=geometry['BodyModule_calf_'+side];signed=[]
        for i,p in enumerate(points):
            if .20<=body['bindHeight'][i]<=.245:
                nearest,normal,_,distance=tree.find_nearest(p)
                signed.append((p-nearest).dot(normal))
        report={'pose':pose,'side':side,'samples':len(signed),'maxOutsideMeters':max(signed),'outsideOver1mm':sum(d>.001 for d in signed)};reports.append(report)
    c=json.loads((OUT/f'{pose}_camera.json').read_text());bpy.ops.object.camera_add();cam=bpy.context.object;cam.location=cv(c['position']);cam.rotation_euler=(cv(c['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.angle=math.radians(c['fov']);cam.data.clip_start=.001
    scene=bpy.context.scene;scene.camera=cam;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.render.resolution_x=700;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/f'Blender_{pose}_after.png');bpy.ops.render.render(write_still=True)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{pose}_posed.blend'))
(OUT/'blender-posed-checks.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
assert all(r['outsideOver1mm']==0 for r in reports), 'Residual calf penetration'
