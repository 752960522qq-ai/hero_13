import bpy,sys,json,numpy as np
from pathlib import Path
ROOT=Path('/workspace/scratch/2c231503b90d/work_v15');sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
from city_surface_sampling import HeightField
from shapely.geometry import Polygon,Point
import shapely
BASE=Path('/workspace/scratch/705f52588668/work_v14/model')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'))
bpy.context.view_layer.update();p=json.loads((BASE/'city_plan.json').read_text())
terrain=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
out=[]
for r in p['buildings']+p['real_buildings']:
    poly=Polygon(r.get('footprint',r.get('footprint_xy')));floor=r.get('base',r.get('floor'));samples=[];inside=[]
    for q in shapely.segmentize(poly.buffer(-.3),2).exterior.coords:
        z=terrain.height(q)
        if z is not None:inside.append(z-floor)
    for q in shapely.segmentize(poly.buffer(.4),3).exterior.coords:
        z=terrain.height(q)
        if z is not None:samples.append(z-floor)
    out.append({'name':r.get('name',r.get('instance_name')),'floor':floor,'center':r['center'],'zone':r.get('zone'),'inside_max':max(inside,default=None),'surround_max':max(samples,default=None),'surround_min':min(samples,default=None)})
(ROOT/'ground_audit_before.json').write_text(json.dumps(out,indent=2))
for r in out:
    if (r['inside_max'] or 0)>.3 or (r['surround_max'] or 0)>1.:print('BURIED',r,flush=True)
inventory=[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'surface_type':o.get('surface_type'),'polygons':len(o.data.polygons) if o.type=='MESH' else 0,'attributes':list(o.data.attributes.keys()) if o.type=='MESH' else []} for o in bpy.context.scene.objects]
(ROOT/'scene_inventory.json').write_text(json.dumps(inventory,indent=2))
