"""Extract the supplied kit's geometry and per-corner UVs without substitutions.

blender -b --factory-startup --python extract_road_assets_blender.py -- \
  --roads road_modular.glb --out road_templates.json
"""
import argparse, json, sys
from pathlib import Path
import bpy

ap=argparse.ArgumentParser()
ap.add_argument('--roads',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.roads.resolve()))
bpy.context.view_layer.update()
names={'local':'Road_33_69','arterial':'Double road_36_7',
       'sidewalk':'Sidewalk 2_1_75','crossing':'Pedestrian crossing_25_63'}
result={}
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    a=o;kind=None
    while a and kind is None:
        kind=next((k for k,v in names.items() if v in a.name),None)
        if kind is None:a=a.parent
    if kind is None:continue
    o.data.calc_loop_triangles();uv=o.data.uv_layers.active.data
    result[kind]={'source_object':a.name,
        'vertices':[list(o.matrix_world@v.co) for v in o.data.vertices],
        'triangles':[{'v':list(t.vertices),'uv':[list(uv[i].uv) for i in t.loops]}
                     for t in o.data.loop_triangles]}
assert set(result)==set(names),set(result)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps(result,separators=(',',':')))
print('SOURCE_ASSETS_EXTRACTED',list(result),flush=True)
