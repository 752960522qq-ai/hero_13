import bpy,re,zipfile,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path('/workspace/sites/xiaqing-motion-lab');OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend');r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];d=o.data;ids={int(re.search(r'tripo_part_(\d+)',m.name).group(1)):i for i,m in enumerate(d.materials)}
d.calc_loop_triangles();tri=[tuple(t.vertices) for t in d.loop_triangles if t.material_index==ids[1]];tree=BVHTree.FromPolygons([v.co for v in d.vertices],tri,all_triangles=True)
mat=d.materials[ids[4]];patch=mat.copy();patch.name='Chest_Hair_Local_Repair';newidx=len(d.materials);d.materials.append(patch);node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');im=bpy.data.images.load('/tmp/newtex/xiaqing_trousers_tripo_part_4_basecolor.jpg',check_existing=False);im.pack();node.image=im;selected=0
for p in d.polygons:
 if p.material_index!=ids[4]:continue
 c=p.center
 if -.105<c.x<-.025 and c.y<-.035 and .655<c.z<.805 and tree.find_nearest(c)[3]<.009:p.material_index=newidx;selected+=1
print('LOCAL_HAIR_FACES',selected,flush=True)
r.animation_data.action=None
for t in r.animation_data.nla_tracks:t.mute=True
for p in r.pose.bones:p.matrix_basis.identity()
bpy.data.orphans_purge(do_recursive=True);bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_image_format='JPEG',export_jpeg_quality=95,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
p=OUT/'texture-shoulder-v53-report.json';j=json.loads(p.read_text());j['hair_repair']['localized_material_faces']=selected;j['hair_repair']['shirt_material_preserved']=True;p.write_text(json.dumps(j,indent=2))
