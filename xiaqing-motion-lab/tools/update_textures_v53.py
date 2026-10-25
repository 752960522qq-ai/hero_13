"""v5.3: retain v5.1 mesh, finish Idle/Walk shoulder correction, apply v2 textures."""
import bpy,math,json,re,hashlib
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/texwork/xiaqing_trousers.blend');r=bpy.data.objects['夏晴_牛仔裤'];body=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
def digest(a):return hashlib.sha256(repr([(f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]) for f in a.fcurves]).encode()).hexdigest()
untouched={n:digest(bpy.data.actions[n]) for n in ['Run','ArmRaise','HandTest']};report=[]
for m in body.modifiers:
 if m.type=='ARMATURE':m.show_viewport=False
for name in ['Idle','Walk']:
 a=bpy.data.actions[name];r.animation_data.action=a;cached=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();cached.append({p.name:p.matrix.copy() for p in r.pose.bones})
 widths=[]
 for frame,pose in enumerate(cached,1):
  s.frame_set(frame)
  for side,sign in [('Left',1),('Right',-1)]:
   sn=side+'Shoulder';sh=r.pose.bones[sn];old=pose[sn];neutral=pose[sh.parent.name]@sh.parent.bone.matrix_local.inverted()@sh.bone.matrix_local;q=old.to_quaternion().slerp(neutral.to_quaternion(),.25)
   sh.matrix=Matrix.Translation(old.translation)@q.to_matrix().to_4x4()@Matrix.Diagonal((.89,.89,.89,1));bpy.context.view_layer.update()
   pivot=pose[side+'Arm'].translation;newpivot=sh.tail.copy();turn=Quaternion((0,1,0),sign*math.radians(3 if name=='Idle' else 5));names=[side+x for x in ['Arm','ForeArm','Hand','Elbow','FingerCurl']]
   targets={n:Matrix.Translation(newpivot+turn@(pose[n].translation-pivot))@(turn@pose[n].to_quaternion()).to_matrix().to_4x4() for n in names}
   for n in sorted(names,key=lambda n:len(r.pose.bones[n].parent_recursive)):
    r.pose.bones[n].matrix=targets[n];bpy.context.view_layer.update()
   arm=r.pose.bones[side+'Arm'];fore=r.pose.bones[side+'ForeArm'];assert (arm.tail-arm.head).angle(fore.tail-fore.head)<.002;assert (sh.tail-arm.head).length<1e-5
   for n in [sn]+names:
    for prop in ['location','rotation_quaternion','scale']:r.pose.bones[n].keyframe_insert(prop,frame=frame,group=n)
  widths.append(((pose['LeftArm'].translation-pose['RightArm'].translation).length,(r.pose.bones['LeftArm'].head-r.pose.bones['RightArm'].head).length))
 for fc in a.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 report.append({'clip':name,'width_before':sum(v[0] for v in widths)/len(widths),'width_after':sum(v[1] for v in widths)/len(widths)})
for n,h in untouched.items():assert digest(bpy.data.actions[n])==h
for m in body.modifiers:
 if m.type=='ARMATURE':m.show_viewport=True
replaced=[];imgs={}
for mat in body.data.materials:
 if not mat or not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type!='TEX_IMAGE' or not node.image:continue
  match=re.search(r'tripo_part_(\d+)',node.image.name) or re.search(r'tripo_part_(\d+)',mat.name)
  if not match:continue
  part=int(match.group(1));p=Path('/tmp/newtex')/f'xiaqing_trousers_tripo_part_{part}_basecolor.jpg'
  assert p.exists()
  if part not in imgs:imgs[part]=bpy.data.images.load(str(p),check_existing=False);imgs[part].pack()
  node.image=imgs[part];replaced.append(part)
assert len(set(replaced))==35,sorted(set(replaced))
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='5.3'
(OUT/'texture-shoulder-v53-report.json').write_text(json.dumps({'textures_replaced':sorted(set(replaced)),'shoulder_corrections':report,'unmodified_actions':untouched,'mesh_uv_weights_unchanged':True},indent=2))
bpy.data.orphans_purge(do_recursive=True);bpy.ops.wm.save_as_mainfile(filepath='/tmp/texwork/staged.blend',compress=True)
