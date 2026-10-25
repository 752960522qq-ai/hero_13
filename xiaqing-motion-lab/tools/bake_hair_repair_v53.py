"""UV-bake generated repair on pale chest-hair bleed; preserve other texels."""
import bpy,bmesh,json,zipfile,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/texwork/staged.blend');s=bpy.context.scene;r=bpy.data.objects['夏晴_牛仔裤'];body=bpy.data.objects['XiaQing_Jeans_Surface'];data=body.data
ids={int(re.search(r'tripo_part_(\d+)',m.name).group(1)):i for i,m in enumerate(data.materials)}
data.calc_loop_triangles();tri=[t for t in data.loop_triangles if t.material_index==ids[1]];tree=BVHTree.FromPolygons([v.co for v in data.vertices],[tuple(t.vertices) for t in tri],all_triangles=True)
fiximage=bpy.data.images.load(str(ROOT/'source-models/hair_repair_reference.png'))
for part in [1,4]:
 idx=ids[part];mat=data.materials[idx];original_node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');original=original_node.image
 mesh=data.copy();ob=bpy.data.objects.new('Hair_Bake_Temp',mesh);s.collection.objects.link(ob);bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=idx],context='FACES');bm.to_mesh(mesh);bm.free()
 mesh.materials.clear();bmat=bpy.data.materials.new('Hair_Repair_Bake');bmat.use_nodes=True;mesh.materials.append(bmat)
 for p in mesh.polygons:p.material_index=0
 if part==4:
  mapped=mesh.uv_layers.new(name='NeighborHairUV');proximity=mesh.attributes.new('HairNear','FLOAT','POINT');near={}
  for v in mesh.vertices:
   loc,n,ti,d=tree.find_nearest(v.co);t=tri[ti];uvs=[Vector((*data.uv_layers.active.data[k].uv,0)) for k in t.loops];uv=barycentric_transform(loc,*[data.vertices[k].co for k in t.vertices],*uvs);near[v.index]=uv;proximity.data[v.index].value=max(0,min(1,(.009-d)/.005))
  for l in mesh.loops:mapped.data[l.index].uv=near[l.vertex_index].xy
  mesh.uv_layers.active_index=0
  for layer in mesh.uv_layers:layer.active_render=(layer==mesh.uv_layers[0])
 nodes=bmat.node_tree.nodes;nodes.clear();links=bmat.node_tree.links
 src=nodes.new('ShaderNodeTexImage');src.image=original;fix=nodes.new('ShaderNodeTexImage');fix.image=fiximage
 uv0=nodes.new('ShaderNodeUVMap');uv0.uv_map=mesh.uv_layers[0].name;links.new(uv0.outputs[0],src.inputs['Vector']);uvf=nodes.new('ShaderNodeUVMap');uvf.uv_map='NeighborHairUV' if part==4 else mesh.uv_layers[0].name;links.new(uvf.outputs[0],fix.inputs['Vector'])
 outimg=original.copy();outimg.name=f'XiaQing_ChestHair_Repaired_{part}';target=nodes.new('ShaderNodeTexImage');target.image=outimg;nodes.active=target
 hsv=nodes.new('ShaderNodeSeparateColor');hsv.mode='HSV';links.new(src.outputs['Color'],hsv.inputs['Color'])
 def mul(a,b):
  n=nodes.new('ShaderNodeMath');n.operation='MULTIPLY';links.new(a,n.inputs[0]);links.new(b,n.inputs[1]);return n.outputs[0]
 def remap(sock,low,high,to1=0,to2=1):
  n=nodes.new('ShaderNodeMapRange');n.clamp=True;n.inputs['From Min'].default_value=low;n.inputs['From Max'].default_value=high;n.inputs['To Min'].default_value=to1;n.inputs['To Max'].default_value=to2;links.new(sock,n.inputs['Value']);return n.outputs['Result']
 color_mask=mul(remap(hsv.outputs[1],.25,.60,1,0),remap(hsv.outputs[2],.16,.30))
 geo=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geo.outputs['Position'],sep.inputs[0]);spatial=mul(remap(sep.outputs['Z'],.645,.665),remap(sep.outputs['Z'],.790,.820,1,0));spatial=mul(spatial,remap(sep.outputs['Y'],-.025,.005,1,0));mask=mul(color_mask,spatial)
 if part==4:
  attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='HairNear';mask=mul(mask,attr.outputs['Fac']);mask=mul(mask,remap(sep.outputs['X'],-.035,-.015,1,0))
 mix=nodes.new('ShaderNodeMixRGB');links.new(mask,mix.inputs[0]);links.new(src.outputs['Color'],mix.inputs[1]);links.new(fix.outputs['Color'],mix.inputs[2]);em=nodes.new('ShaderNodeEmission');links.new(mix.outputs[0],em.inputs['Color']);output=nodes.new('ShaderNodeOutputMaterial');links.new(em.outputs[0],output.inputs['Surface'])
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;s.render.engine='CYCLES';s.cycles.samples=1;s.render.bake.use_clear=False;s.render.bake.margin=1;s.render.bake.use_selected_to_active=False
 bpy.ops.object.bake(type='EMIT',uv_layer=mesh.uv_layers[0].name);outimg.filepath_raw=str(ROOT/f'source-models/hair_chest_repaired_{part}.png');outimg.file_format='PNG';outimg.save();outimg.pack();original_node.image=outimg;bpy.data.objects.remove(ob,do_unlink=True);print('REPAIRED',part,flush=True)
bpy.data.orphans_purge(do_recursive=True)
p=OUT/'texture-shoulder-v53-report.json';report=json.loads(p.read_text());report['hair_repair']={'method':'generated hair color, UV-projected and emission-baked with chest/brightness/saturation/proximity masks','parts':[1,4],'geometry_changed':False,'region_z':[.645,.820]};p.write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);body.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
print('FINISHED',len(data.vertices),'vertices',flush=True)
