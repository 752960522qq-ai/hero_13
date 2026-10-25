import bpy,math,json,zipfile,re
from pathlib import Path
ROOT=Path('/workspace/sites/xiaqing-motion-lab');out=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend')
o=bpy.data.objects['XiaQing_Jeans_Surface'];r=bpy.data.objects['夏晴_牛仔裤'];d=o.data
for t in r.animation_data.nla_tracks:t.mute=True
# Only shirt and exposed upper arm: exclude overlying hair.
eligible=set()
for p in d.polygons:
 if d.materials[p.material_index].name in ['tripo_part_4_material','tripo_part_10_material','tripo_part_11_material']:eligible.update(p.vertices)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
changed=[]
for v in d.vertices:
 x,y,z=v.co;a=abs(x)
 if v.index not in eligible or not (.075<a<.15 and .695<z<.788):continue
 side='Left' if x>0 else 'Right';arm=o.vertex_groups[side+'Arm'];spine=o.vertex_groups['Spine2'];w={g.group:g.weight for g in v.groups};old=w.get(arm.index,0)
 if old<.005:continue
 # Broader, soft lower-arm/torso transition, limited to a modest weight transfer.
 mask=smooth(.695,.718,z)*(1-smooth(.755,.788,z))*smooth(.075,.09,a)*(1-smooth(.138,.15,a))
 target=smooth(.09,.145,a);delta=max(-.18,min(.18,target-old))*.65*mask
 if abs(delta)<.0001:continue
 if delta>0:delta=min(delta,w.get(spine.index,0))
 if abs(delta)<.0001:continue
 arm.add([v.index],old+delta,'REPLACE');spine.add([v.index],w.get(spine.index,0)-delta,'REPLACE');changed.append(v.index)
assert changed
checks=[]
for label,frame in [('Idle',1),('Walk',10),('Run',9),('ArmRaise',60)]:
 r.animation_data.action=bpy.data.actions[label];bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());assert all(math.isfinite(c) for i in changed for c in e.data.vertices[i].co);checks.append(label)
for i in changed:assert abs(sum(g.weight for g in d.vertices[i].groups)-1)<1e-5
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
r['version']='5.4';bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_axilla_v54.blend',compress=True)
with zipfile.ZipFile(out/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:z.write('/tmp/xiaqing_axilla_v54.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_image_format='JPEG',export_jpeg_quality=95,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
report={'version':'5.4','changed_vertices':len(changed),'scope':'lower axilla skin weights only','animation_data_unchanged':True,'normalized_weights':True,'finite_pose_checks':checks}
(out/'axilla-v54-report.json').write_text(json.dumps(report,indent=2));print(report)
