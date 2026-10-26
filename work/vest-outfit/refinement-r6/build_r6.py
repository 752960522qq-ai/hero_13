"""Rebuild the saved reference workspace from R5 and the reviewed local patch."""
import bpy,runpy,sys
from pathlib import Path
P=Path(__file__).resolve().parent
baseline=P.parent/'refinement-r5/vest_xiaqing_r5.blend'
if not baseline.exists():baseline=P/'vest_xiaqing_r6.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
# The final snapshot carries its own complete rig, weights and actions, so the
# archive can be rebuilt without keeping obsolete R2-R5 binary snapshots.
for obj in list(bpy.data.objects):
 if obj.get('comparison_only'):bpy.data.objects.remove(obj,do_unlink=True)
for collection in list(bpy.data.collections):
 if collection.name.startswith('REFERENCE_') and not collection.objects:bpy.data.collections.remove(collection)
runpy.run_path(str(P/'lower_restore/apply_lower.py'))['apply_lower']()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'rigged_body.blend'),compress=True)
sys.argv=['create_reference_scene.py','--',str(P/'rigged_body.blend')]
runpy.run_path(str(P/'create_reference_scene.py'),run_name='__main__')
