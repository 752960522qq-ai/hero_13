import bpy,json,struct,math,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;AS=P.parents[2]/'dist/assets';report=json.loads((P/'report.json').read_text())
for outfit in ['vest','green_t','floral_dress','school_uniform']:
 file=AS/(outfit+'_xiaqing.glb');b=file.read_bytes();ln=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+ln]);binary=b[28+ln:]
 for a in j['animations']:
  if a['name']=='FiringRifle':a['name']='Fire'
 jb=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();jb+=b' '*((-len(jb))%4);file.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(binary))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(binary),0x004e4942)+binary)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(file));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');scene=bpy.context.scene
 for tr in t.animation_data.nla_tracks:tr.mute=True
 for ob in bpy.context.scene.objects:
  if ob.type=='MESH' and not any(m.type=='ARMATURE' for m in ob.modifiers):ob.hide_render=True;ob.hide_set(True)
 if 'FiringRifle' in report[outfit]:report[outfit]['Fire']=report[outfit].pop('FiringRifle')
 for label in ['Jump','Fire']:
  action=next(a for a in bpy.data.actions if a.name==label+'_'+t.name);t.animation_data.action=action;start,end=map(float,action.frame_range);samples=[];allmin=[]
  for f in np.linspace(start,end,15):
   scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();z=[]
   for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not any(m.type=='ARMATURE' for m in ob.modifiers):continue
    eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();z.append(min((eo.matrix_world@v.co).z for v in me.vertices));eo.to_mesh_clear()
   allmin.append(min(z))
  # Ground for jump should use landing/launch feet, never remove the intentional airborne root height.
  base=min(allmin)
  report[outfit][label]['ground']=-base;report[outfit][label]['groundSampleMin']=min(allmin);report[outfit][label]['sole_samples_m']=allmin
  if outfit in ['vest','green_t']:
   f=(start+end)/2;scene.frame_set(int(f),subframe=f-int(f));scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='TEXTURE';scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.color=(.8,.8,.8);scene.render.resolution_x=650;scene.render.resolution_y=750;scene.render.resolution_percentage=100
   cam=bpy.data.objects.new('AdaptationReviewCamera',bpy.data.cameras.new('Review'));scene.collection.objects.link(cam);scene.camera=cam;target=Vector((0,0,1));cam.location=Vector((2.5,-3.5,1.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.2;scene.render.filepath=str(P/(outfit+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
  print('GROUND',outfit,label,-base,allmin,flush=True)
 bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/(outfit+'_r21.blend')),compress=True)
 (P/'report.json').write_text(json.dumps(report,indent=2))
print('FINAL_READY',flush=True)
