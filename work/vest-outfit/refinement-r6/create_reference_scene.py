"""Place the untouched source vest character beside the R5 rig in Blender."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parent
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
INPUT=Path(argv[0]) if argv else ROOT/'refinement-r5/vest_xiaqing_r5.blend'
tag='after' if argv else 'before'
bpy.ops.wm.open_mainfile(filepath=str(INPUT))
r=bpy.data.objects['Xiaqing_Native_Rig'];r.animation_data.action=None;r.data.pose_position='REST'
for t in r.animation_data.nla_tracks:t.mute=True
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(P/'reference_original.glb'))
ref=bpy.data.collections.new('REFERENCE_original_vest_uniform_scale');bpy.context.scene.collection.children.link(ref)
for o in set(bpy.data.objects)-before:
 for c in list(o.users_collection):c.objects.unlink(o)
 ref.objects.link(o)
 o['comparison_only']=True
 if o.type=='MESH':
  o.name='REFERENCE_original_vest_body';o.scale*=1.7;o.location+=Vector((1.10-.00023407833465015,-.1259081221330608,-.00964825950517234));o['comparison_only']=True;o['source_shape_untouched']=True
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=1400;s.render.resolution_y=1100;s.render.resolution_percentage=100
c=s.camera;target=Vector((.55,0,.84));c.location=target+Vector((0,-4,.02));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=2.6
bpy.context.preferences.filepaths.save_version=0
OUT=P/'vest_xiaqing_r6.blend' if argv else P/'reference_before.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
s.render.filepath=str(P/('reference_'+tag+'_Rest.png'));bpy.ops.render.render(write_still=True)
# The raw source stays in its authored A pose. Sampled animation rendering is
# saved separately so the source reference is never warped to imitate a pose.
if argv:
 r.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith('Idle'));r.animation_data.action=a;s.frame_set(round(a.frame_range[1]*.35));s.render.filepath=str(P/'reference_after_Idle.png');bpy.ops.render.render(write_still=True)
print('SIDE_BY_SIDE_REFERENCE_CREATED')
