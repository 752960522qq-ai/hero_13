import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;UPLOAD=Path('/workspace/scratch/7b171b7361b3/upload')
for label,file in [('Idle','girl_Idle(1).fbx'),('Walk','girl Walk(1).fbx'),('Run','Running(4).fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(UPLOAD/file));r=next(o for o in bpy.data.objects if o.type=='ARMATURE');a=r.animation_data.action;a.name=label;s=bpy.context.scene;s.render.fps=30;s.frame_start=round(a.frame_range[0]);s.frame_end=round(a.frame_range[1]);s.frame_set(s.frame_start)
 for b in r.data.bones:b.name=b.name.split(':')[-1]
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.gltf(filepath=str(ROOT/'source-motions'/f'{label}_raw.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=False)
 print('RAW_SOURCE',label,s.frame_start,s.frame_end,len(r.data.bones),flush=True)
