"""Reimport the complete city GLB and check building scale and site interfaces."""
from pathlib import Path
import argparse,json,sys,numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField
ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--placements',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);placement=json.loads(args.placements.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()));bpy.context.view_layer.update()
def below(o,name):
    while o:
        if o.name==name:return True
        o=o.parent
    return False
def bvh(objects,flat=False):
    v=[];f=[]
    for o in objects:
        off=len(v);q=[o.matrix_world@p.co for p in o.data.vertices]
        if flat:q=[Vector((p.x,p.y,0)) for p in q]
        v.extend(q);o.data.calc_loop_triangles();f.extend(tuple(off+i for i in t.vertices) for t in o.data.loop_triangles)
    return BVHTree.FromPolygons(v,f,all_triangles=True,epsilon=.001)
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];terrain=HeightField([o for o in objects if 'Sculpted_Terrain' in o.name]);walk=HeightField([o for o in objects if below(o,'06_SIDEWALKS')]);roads_flat=bvh([o for o in objects if o.name.startswith('Continuous_Pavement_Repaired')],True)
def height(tree,xy):
    if isinstance(tree,HeightField):return tree.height(xy)
    hit,*_=tree.ray_cast(Vector((float(xy[0]),float(xy[1]),500)),Vector((0,0,-1)),1000)
    return None if hit is None else float(hit.z)
instances=[o for o in bpy.context.scene.objects if o.get('is_building_instance')];assert len(instances)==2
results=[];failures=[]
for r in placement['instances']:
    inst=next(o for o in instances if o.name==r['instance_name']);parts=[o for o in objects if below(o,inst.name)];assert len(parts)==r['source_mesh_count']==1
    q=np.vstack([np.array([o.matrix_world@v.co for v in o.data.vertices]) for o in parts]);lo=q.min(0);hi=q.max(0);height_error=abs(hi[2]-lo[2]-r['target_height_m']);base_error=abs(lo[2]-r['building_base_m'])
    axes=np.linalg.norm(np.array(inst.matrix_world)[:3,:3],axis=0);uniform_error=float(axes.max()-axes.min());assert height_error<.002 and base_error<.002 and uniform_error<.0001
    assert all(o.data.uv_layers.active is not None for o in parts)
    pad=bpy.data.objects[inst.name+'_Level_Foundation'];rectangle=np.array(r['footprint_xy']);a=rectangle[0];u=rectangle[1]-a;v=rectangle[3]-a
    xs=np.linspace(0,1,int(np.ceil(np.linalg.norm(u)))+1);ys=np.linspace(0,1,int(np.ceil(np.linalg.norm(v)))+1)
    road_hits=0;ground_min=1e9;ground_max=-1e9
    for x in xs:
        for y in ys:
            xy=a+x*u+y*v;h=height(terrain,xy)
            assert h is not None,'Foundation crosses a terrain cut'
            ground_min=min(ground_min,h);ground_max=max(ground_max,h)
            if height(roads_flat,xy) is not None:road_hits+=1
    print('CBD_FOOTING_CHECK',inst.name,road_hits,ground_min,ground_max,r['foundation_top_m'],r['foundation_bottom_m'],flush=True)
    assert road_hits==0 and r['foundation_top_m']-ground_max>.02 and ground_min-r['foundation_bottom_m']>.15,(road_hits,ground_min,ground_max,r['foundation_top_m'],r['foundation_bottom_m'])
    approach=bpy.data.objects[inst.name+'_Sidewalk_Access'];ab=HeightField([approach]);missing=0;buried=0;minimum_clearance=1e9;bad_samples=[]
    start=np.array(r['access_start_xy']);end=np.array(r['access_end_xy']);d=end-start;L=np.linalg.norm(d);n=np.array([-d[1],d[0]])/L
    for t in np.linspace(.0002,.9998,int(L/.25)+1):
        for offset in np.linspace(-1.48,1.48,7):
            xy=start+d*t+n*offset;h=height(ab,xy);land=height(terrain,xy)
            if h is None:missing+=1;bad_samples.append({'xy':xy.tolist(),'reason':'missing'});continue
            if land is not None:
                minimum_clearance=min(minimum_clearance,h-land)
                if land>h+.005:buried+=1;bad_samples.append({'xy':xy.tolist(),'reason':'terrain','surface':h,'terrain':land})
    lips=[];lip_details=[]
    for offset in np.linspace(-1.48,1.48,7):
        xy=end-d/L*.006+n*offset
        z1=height(ab,xy);z2=height(walk,xy);assert z1 is not None and z2 is not None;lips.append(abs(z1-z2));lip_details.append([xy.tolist(),z1,z2])
    print('CBD_ACCESS_CHECK',inst.name,missing,buried,minimum_clearance,max(lips),json.dumps({'bad_samples':bad_samples[:8],'endpoints':lip_details}),flush=True)
    if missing or buried or max(lips)>=.015 or r['access_maximum_grade']>=.06:failures.append({'instance':inst.name,'missing':missing,'buried':buried,'minimum_clearance':minimum_clearance,'maximum_lip':max(lips),'bad_samples':bad_samples})
    other=[o for o in objects if o.get('is_placeholder')]
    # Convex rectangle overlap, including the other newly placed ground apron.
    polygons=[]
    for o in other:
        co=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);mi=co[:,:2].min(0);ma=co[:,:2].max(0);polygons.append(np.array([[mi[0],mi[1]],[ma[0],mi[1]],[ma[0],ma[1]],[mi[0],ma[1]]]))
    polygons.extend(np.array(v['footprint_xy']) for v in placement['instances'] if v['instance_name']!=inst.name)
    def overlap(p,q):
        for poly in [p,q]:
            for e in np.roll(poly,-1,0)-poly:
                n=np.array([-e[1],e[0]]);a=p@n;b=q@n
                if a.max()<=b.min() or b.max()<=a.min():return False
        return True
    assert not any(overlap(rectangle,p) for p in polygons),'CBD lot overlaps a neighbour'
    results.append({'instance':inst.name,'source':r['source_filename'],'height_m':float(hi[2]-lo[2]),'height_error_m':height_error,'uniform_scale_axis_error':uniform_error,'source_mesh_instances':len(parts),'foundation_top_clearance_min_m':r['foundation_top_m']-ground_max,'buried_footing_depth_min_m':ground_min-r['foundation_bottom_m'],'road_overlap_samples':road_hits,'access_missing_samples':missing,'access_terrain_penetrations':buried,'access_minimum_terrain_clearance_m':minimum_clearance,'access_maximum_grade':r['access_maximum_grade'],'access_end_maximum_lip_m':max(lips)})
assert placement['original_geometry_sha256_before']==placement['original_geometry_sha256_after']
report={'glb_reimport_success':True,'building_instance_count':len(instances),'original_road_sidewalk_terrain_unchanged':True,'placeholder_object_count':sum(o.get('is_placeholder',False) for o in objects),'placeholder_building_count':sum(bool(o.get('is_placeholder',False) and o.get('district')) for o in objects),'buildings':results,'failures':failures,'validation_passed':not failures}
args.report.write_text(json.dumps(report,indent=2));print('CBD_VALIDATION_RESULT',json.dumps(report,indent=2),flush=True)
assert not failures,'CBD site interface validation failed; inspect report'
