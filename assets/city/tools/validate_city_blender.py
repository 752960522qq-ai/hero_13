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
optimized=plan.get('schema')=='hero13.city.blockout.v2'
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
    return BVHTree.FromPolygons(verts,faces,all_triangles=True,epsilon=.001)
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
roads=[o for o in objs if ancestor(o,'03_ROAD_NETWORK')]
walks=[o for o in objs if ancestor(o,'06_SIDEWALKS')]
land=[o for o in objs if 'Sculpted_Terrain' in o.name]
assert len(roads)>=(4 if optimized else 61) and len(land)==3,(len(roads),len(land))
rb=bvh(roads);tb=bvh(land)
pavement_components=None
if optimized:
    continuous=next(o for o in roads if o.name.startswith('Continuous_Pavement_Repaired'))
    vv=np.array([continuous.matrix_world@v.co for v in continuous.data.vertices])
    continuous.data.calc_loop_triangles();ff=np.array([t.vertices[:] for t in continuous.data.loop_triangles],np.int32)
    _,ids=np.unique(np.rint(vv/.001).astype(np.int64),axis=0,return_inverse=True)
    parent=np.arange(int(ids.max())+1)
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return int(i)
    for a,b,c in ids[ff]:
        ra=root(int(a));rb0=root(int(b));rc=root(int(c));parent[rb0]=ra;parent[rc]=ra
    pp=vv[ff];areas=np.abs((pp[:,1,0]-pp[:,0,0])*(pp[:,2,1]-pp[:,0,1])-(pp[:,1,1]-pp[:,0,1])*(pp[:,2,0]-pp[:,0,0]))/2
    component_area={}
    for a,area in zip(ids[ff[:,0]],areas):
        r=root(int(a));component_area[r]=component_area.get(r,0)+float(area)
    pavement_components=sum(area>1 for area in component_area.values())
    assert pavement_components==1,'Exported continuous pavement mesh is disconnected'
terrain_downward=0
for o in land:
    vv=np.array([o.matrix_world@v.co for v in o.data.vertices]);o.data.calc_loop_triangles()
    ff=np.array([list(t.vertices) for t in o.data.loop_triangles],dtype=np.int32);pp=vv[ff]
    cross=(pp[:,1,0]-pp[:,0,0])*(pp[:,2,1]-pp[:,0,1])-(pp[:,1,1]-pp[:,0,1])*(pp[:,2,0]-pp[:,0,0])
    terrain_downward+=int(np.sum(cross<-.00001))
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
walk_missing=[];walk_buried=[];walk_tests=0;walk_errors=[]
if optimized:
    assert len(walks)>=4,'Standalone source sidewalks were not exported'
    wb=bvh(walks)
    samples=np.load(plan_path.parent/'sidewalk_validation_samples.npz')['samples']
    for q in samples:
        hit,_,_,_=wb.ray_cast(Vector((q[0],q[1],q[2]+3)),Vector((0,0,-1)),7)
        walk_tests+=1
        if hit is None:
            walk_missing.append(q.round(4).tolist());continue
        walk_errors.append(abs(hit.z-q[2]-.143577))
        terrain,_,_,_=tb.ray_cast(Vector((q[0],q[1],q[2]+4)),Vector((0,0,-1)),10)
        if terrain is not None and terrain.z>hit.z+.04:walk_buried.append(q.round(4).tolist())
stats={'glb_reimport_success':True,'mesh_objects':len(objs),'road_meshes':len(roads),'sample_rays':tests,'road_surface_missing_samples':len(missing),'road_surface_height_error_p99_m':float(np.percentile(road_errors,99)),'terrain_sample_rays':terrain_tests,'road_buried_samples':len(buried),'maximum_terrain_penetration_m':max((x['penetration_m'] for x in buried),default=0),'maximum_junction_endpoint_error_m':endpoint_error,'terrain_method':'Road footprints replace terrain; terrain holes beneath pavement are intentional.','plan':plan['stats']}
if optimized:stats.update(sidewalk_meshes=len(walks),sidewalk_sample_rays=walk_tests,sidewalk_missing_samples=len(walk_missing),sidewalk_buried_samples=len(walk_buried),sidewalk_height_error_p99_m=float(np.percentile(walk_errors,99)))
stats['terrain_downward_triangles']=terrain_downward
stats['ray_geometry_tolerance_m']=.001
if optimized:stats['pavement_mesh_components_over_1m2']=pavement_components
report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps({'stats':stats,'missing':missing,'buried':buried,'sidewalk_missing':walk_missing,'sidewalk_buried':walk_buried},indent=2))
print('CITY_VALIDATION',json.dumps(stats,indent=2),flush=True)
assert not missing,'Missing road samples; inspect report'
assert not buried,'Terrain intersects the driveable pavement'
assert endpoint_error<.001,'Junction endpoint elevations disagree'
assert plan['stats']['connected_components']==1,'Road graph is disconnected'
assert not walk_missing,'Missing sidewalks; inspect report'
assert not walk_buried,'Terrain protrudes through sidewalk'
if optimized:assert terrain_downward==0,'Terrain road-shoulder triangles point downwards'
