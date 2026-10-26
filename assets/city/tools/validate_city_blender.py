"""Reimport the deliverable GLB; check route coverage and terrain clearance."""
import bpy, json, math, sys, argparse
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ap=argparse.ArgumentParser();ap.add_argument('base',type=Path,nargs='?');ap.add_argument('--plan',type=Path);ap.add_argument('--glb',type=Path);ap.add_argument('--report',type=Path);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.base:
    plan_path=args.base/'work/plan/city_plan.json';glb_path=args.base/'output/huizhou_road_network.glb';report_path=args.base/'work/validation.json'
else:
    assert args.plan and args.glb and args.report,'Provide --plan, --glb and --report'
    plan_path=args.plan;glb_path=args.glb;report_path=args.report
plan=json.loads(plan_path.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(glb_path))
bpy.context.view_layer.update()
# glTF is converted back to Blender's Z-up basis by Blender's own importer.
def ancestor(o,name):
    while o:
        if o.name.startswith(name):return True
        o=o.parent
    return False
def bvh(objects):
    verts=[];faces=[]
    for o in objects:
        off=len(verts);verts.extend([o.matrix_world@v.co for v in o.data.vertices]);o.data.calc_loop_triangles()
        faces.extend([tuple(off+i for i in p.vertices) for p in o.data.loop_triangles])
    return BVHTree.FromPolygons(verts,faces,all_triangles=True)
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
roads=[o for o in objs if ancestor(o,'03_ROAD_NETWORK')]
land=[o for o in objs if 'Sculpted_Terrain' in o.name]
assert len(roads)>60 and len(land)==3,(len(roads),len(land))
rb=bvh(roads);tb=bvh(land)
missing=[];buried=[];road_errors=[];tests=0;terrain_tests=0
for ei,e in enumerate(plan['edges']):
    p=np.array(e['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
    for s in np.linspace(0,ds[-1],max(2,int(ds[-1]/14)+1)):
        center=np.array([np.interp(s,ds,p[:,i]) for i in range(3)])
        lo=max(0,s-.5);hi=min(ds[-1],s+.5);t=np.array([np.interp(hi,ds,p[:,i])-np.interp(lo,ds,p[:,i]) for i in range(2)]);t/=max(np.linalg.norm(t),1e-6);n=np.array([-t[1],t[0]])
        for offset in [0,-e['width']*.24,e['width']*.24]:
            q=center.copy();q[:2]+=n*offset
            hit,normal,index,distance=rb.ray_cast(Vector((q[0],q[1],q[2]+4)),Vector((0,0,-1)),10)
            tests+=1
            if hit is None:
                missing.append({'edge':ei,'route':e['name'],'xy':q[:2].round(3).tolist(),'s':round(s,2),'offset':offset});continue
            road_errors.append(abs(hit.z-q[2]))
            if not e['bridge']:
                terrain,_,_,_=tb.ray_cast(Vector((q[0],q[1],q[2]+6)),Vector((0,0,-1)),20)
                if terrain:
                    terrain_tests+=1
                    if terrain.z>hit.z+.08:buried.append({'edge':ei,'route':e['name'],'xy':q[:2].round(3).tolist(),'penetration_m':round(terrain.z-hit.z,3)})
endpoint_error=max(max(abs(e['points'][0][2]-plan['nodes'][e['a']]['z']),abs(e['points'][-1][2]-plan['nodes'][e['b']]['z'])) for e in plan['edges'])
stats={'glb_reimport_success':True,'mesh_objects':len(objs),'road_meshes':len(roads),'sample_rays':tests,'road_surface_missing_samples':len(missing),'road_surface_height_error_p99_m':float(np.percentile(road_errors,99)),'terrain_sample_rays':terrain_tests,'road_buried_samples':len(buried),'maximum_terrain_penetration_m':max((x['penetration_m'] for x in buried),default=0),'maximum_junction_endpoint_error_m':endpoint_error,'terrain_method':'Road footprints replace terrain; terrain holes beneath pavement are intentional.','plan':plan['stats']}
report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps({'stats':stats,'missing':missing,'buried':buried},indent=2))
print('CITY_VALIDATION',json.dumps(stats,indent=2),flush=True)
assert not missing,'Missing road samples; inspect report'
assert not buried,'Terrain intersects the driveable pavement'
assert endpoint_error<.001,'Junction endpoint elevations disagree'
assert plan['stats']['connected_components']==1,'Road graph is disconnected'
