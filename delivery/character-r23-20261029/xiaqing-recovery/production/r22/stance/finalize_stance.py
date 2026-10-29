import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;AS=(P.parents[2]/'dist/assets') if (P.parents[2]/'dist/assets').exists() else Path('/workspace/recovered-xiaqing-site/dist/assets');reports={}
for outfit in ['school_uniform','floral_dress']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(AS/(outfit+'_xiaqing.glb')));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');s=bpy.context.scene
 for tr in t.animation_data.nla_tracks:tr.mute=True
 for ob in s.objects:
  if ob.type=='MESH' and not any(m.type=='ARMATURE'for m in ob.modifiers):ob.hide_render=True;ob.hide_set(True)
 reports[outfit]={}
 for label in ['Aim','RifleIdle','Reload','Fire','PistolIdle','RifleRun']:
  a=next(a for a in bpy.data.actions if a.name==label+'_'+t.name);t.animation_data.action=a;start,end=map(float,a.frame_range);mins=[];footmetrics=[]
  for f in np.linspace(start,end,15):
   s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();pts=[]
   for ob in s.objects:
    if ob.type!='MESH'or not any(m.type=='ARMATURE'for m in ob.modifiers):continue
    eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();pts.extend(tuple(eo.matrix_world@v.co)for v in me.vertices);eo.to_mesh_clear()
   pts=np.array(pts);mins.append(float(pts[:,2].min()));low=pts[pts[:,2]<.3]
   if label!='RifleRun' and len(low):
    metrics={}
    for side in ['l','r']:
     ankle=(t.matrix_world@t.pose.bones[side+'_leg_ankle'].matrix).translation
     other=(t.matrix_world@t.pose.bones[('r'if side=='l'else'l')+'_leg_ankle'].matrix).translation
     dist=(low[:,0]-ankle.x)**2+(low[:,1]-ankle.y)**2;dist2=(low[:,0]-other.x)**2+(low[:,1]-other.y)**2;foot=low[(dist<dist2)&(dist<.1)]
     lo,hi=np.quantile(foot[:,1],[.25,.75]);toe=foot[foot[:,1]<=lo,2].min();heel=foot[foot[:,1]>=hi,2].min();metrics[side]={'toe_bottom':float(toe),'heel_bottom':float(heel),'heel_toe_bottom_delta':float(heel-toe)}
    footmetrics.append(metrics)
  reports[outfit][label]={'ground':-min(mins),'sole_min_samples':mins,'static_lower_body':label!='RifleRun','heel_toe_samples':footmetrics[:1]}
  if label in ['Fire','RifleRun']:
   f=(start+end)/2;s.frame_set(int(f),subframe=f-int(f));s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.light='STUDIO';s.display.shading.show_shadows=True;s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('World');s.world.color=(.75,.75,.75);s.render.resolution_x=700;s.render.resolution_y=850;s.render.resolution_percentage=100
   bpy.ops.object.camera_add(location=(3,-.8,1.2));cam=bpy.context.object;target=Vector((0,0,.85));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.0;s.camera=cam;s.render.filepath=str(P/(outfit+'_'+label+'_after.png'));bpy.ops.render.render(write_still=True)
  print('GROUND',outfit,label,-min(mins),footmetrics[:1],flush=True)
 # Save editable packed scene with all original and revised animations available.
 t.animation_data.action=next(a for a in bpy.data.actions if a.name=='RifleIdle_'+t.name);s.frame_set(1);bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/(outfit+'_r22.blend')),compress=True)
 (P/'ground_report.json').write_text(json.dumps(reports,indent=2))
print('DONE',flush=True)
