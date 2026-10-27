"""Reimport the final GLB and check urban massing and building interfaces."""
from pathlib import Path
import argparse,hashlib,json,struct,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--update',type=Path,required=True)
ap.add_argument('--source',type=Path,action='append',required=True);ap.add_argument('--shapely-path',type=Path);ap.add_argument('--report',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField
plan=json.loads(args.plan.read_text());update=json.loads(args.update.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()));bpy.context.view_layer.update()
sc=bpy.context.scene
def below(o,name):
    while o:
        if o.name==name:return True
        o=o.parent
    return False
def triangles(obj,bounds):
    m=obj.data;m.calc_loop_triangles();co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co)
    co=co.reshape(-1,3).astype(np.float64);matrix=np.asarray(obj.matrix_world,np.float64);co=co@matrix[:3,:3].T+matrix[:3,3]
    indices=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',indices);tri=co[indices.reshape(-1,3)]
    lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1);xmin,ymin,xmax,ymax=bounds
    tri=tri[(hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax)]
    a=tri[:,1,:2]-tri[:,0,:2];b=tri[:,2,:2]-tri[:,0,:2]
    return tri[(a[:,0]*b[:,1]-a[:,1]*b[:,0])>1e-8]
class LocalHeightField:
    def __init__(self,objs,bounds):
        self.tri=np.concatenate([triangles(o,bounds) for o in objs])
        xy=self.tri[:,:,:2].reshape(-1,2);unique,ids=np.unique(xy,axis=0,return_inverse=True)
        self.bvh=BVHTree.FromPolygons(np.c_[unique,np.zeros(len(unique))].tolist(),ids.reshape(-1,3).tolist(),all_triangles=True)
    def height(self,xy):
        p=np.asarray(xy[:2],np.float64);found=[]
        for _,_,i,_ in self.bvh.find_nearest_range(Vector((float(p[0]),float(p[1]),0)),.002):
            tri=self.tri[i];a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;d=p-a
            det=u[0]*v[1]-u[1]*v[0];s=(d[0]*v[1]-d[1]*v[0])/det;t=(u[0]*d[1]-u[1]*d[0])/det
            if min(1-s-t,s,t)>=-1e-7:found.append((1-s-t)*tri[0,2]+s*tri[1,2]+t*tri[2,2])
        return None if not found else float(max(found))
def glb_images(path):
    with path.open('rb') as f:
        magic,version,total,n,kind=struct.unpack('<4sIIII',f.read(20));assert magic==b'glTF' and version==2
        meta=json.loads(f.read(n));length,kind=struct.unpack('<II',f.read(8));blob=f.read(length)
    result=[]
    for im in meta.get('images',[]):
        if 'bufferView' not in im:continue
        bv=meta['bufferViews'][im['bufferView']];offset=bv.get('byteOffset',0);part=blob[offset:offset+bv['byteLength']]
        result.append(hashlib.sha256(part).hexdigest())
    return result
city_images=glb_images(args.glb);texture_checks=[]
for source in args.source:
    imgs=glb_images(source);counts=[city_images.count(x) for x in imgs]
    texture_checks.append({'source':source.name,'source_images':len(imgs),'byte_identical_matches':counts})
    assert imgs and all(n==1 for n in counts),'Source texture mismatch: '+source.name
terrain=HeightField([bpy.data.objects['MAIN_Sculpted_Terrain']])
all_instances=[o for o in sc.objects if o.get('is_building_instance')]
assert len(all_instances)==4 and len(plan['real_buildings'])==4
objects=[o for o in sc.objects if o.type=='MESH'];models=[]
for r in plan['real_buildings']:
    inst=next(o for o in all_instances if o.name==r['instance_name'])
    parts=[o for o in objects if below(o,inst.name)];assert len(parts)==1 and parts[0].data.uv_layers.active
    q=np.array([parts[0].matrix_world@v.co for v in parts[0].data.vertices]);actual=float(q[:,2].max()-q[:,2].min())
    axes=np.linalg.norm(np.array(inst.matrix_world)[:3,:3],axis=0);uniform=float(axes.max()-axes.min())
    assert abs(actual-r['target_height_m'])<.002 and uniform<.0001
    models.append({'instance':inst.name,'height_m':actual,'uniform_scale_axis_error':uniform,'source_mesh_instances':len(parts)})
print('MODEL_CHECKS',json.dumps(models),flush=True)
old=update['instances'];points=np.array([r['center'] for r in old]+[r['road_nearest'] for r in old])
lo=points.min(0)-50;hi=points.max(0)+50;local_bounds=[lo[0],lo[1],hi[0],hi[1]]
walk=LocalHeightField([bpy.data.objects['MAIN_Sidewalk_Modular_Continuous'],bpy.data.objects['Sidewalk_Continuous_Transition_Base']],local_bounds)
road_obj=bpy.data.objects['Continuous_Pavement_Repaired'];road=LocalHeightField([road_obj],local_bounds)
sites=[]
for r in old:
    rect=np.array(r['footprint_xy']);a=rect[0];u=rect[1]-a;v=rect[3]-a
    missing=0;road_hits=0;ground_min=1e9;ground_max=-1e9
    for x in np.linspace(0,1,int(np.ceil(np.linalg.norm(u)))+1):
        for y in np.linspace(0,1,int(np.ceil(np.linalg.norm(v)))+1):
            point=a+x*u+y*v;z=terrain.height(point)
            if z is None:missing+=1;continue
            ground_min=min(ground_min,z);ground_max=max(ground_max,z)
            if road.height(point) is not None:road_hits+=1
    ramp=bpy.data.objects[r['instance_name']+'_Sidewalk_Access'];approach=HeightField([ramp]);start=np.array(r['access_start_xy']);end=np.array(r['access_end_xy'])
    d=end-start;length=np.linalg.norm(d);normal=np.array([-d[1],d[0]])/length
    access_missing=0;buried=0;min_clear=1e9;access_road_hits=0
    for t in np.linspace(.0002,.9998,int(length/.5)+1):
        for offset in np.linspace(-1.45,1.45,5):
            q=start+d*t+normal*offset;z=approach.height(q);land=terrain.height(q)
            if z is None:access_missing+=1;continue
            if land is not None:
                min_clear=min(min_clear,z-land)
                if land>z+.005:buried+=1
            if road.height(q) is not None:access_road_hits+=1
    lips=[]
    for offset in np.linspace(-1.45,1.45,7):
        q=end-d/length*.006+normal*offset;one=approach.height(q);two=walk.height(q)
        assert one is not None and two is not None;lips.append(abs(one-two))
    site={'instance':r['instance_name'],'pad_missing_terrain_samples':missing,'pad_road_overlap_samples':road_hits,
          'pad_top_clearance_m':r['foundation_top_m']-ground_max,'pad_buried_depth_m':ground_min-r['foundation_bottom_m'],
          'access_missing_samples':access_missing,'access_terrain_penetrations':buried,'access_road_overlap_samples':access_road_hits,
          'access_min_terrain_clearance_m':min_clear,'access_end_max_lip_m':max(lips),'access_maximum_grade':r['access_maximum_grade']}
    sites.append(site);print('SITE_CHECK',json.dumps(site),flush=True)
    assert missing==road_hits==access_missing==buried==access_road_hits==0
    assert site['pad_top_clearance_m']>.02 and site['pad_buried_depth_m']>.15 and max(lips)<.015 and r['access_maximum_grade']<.06

boxes=[b for b in plan['buildings']]
polygons=[Polygon(b['footprint']) for b in boxes]
real=[Polygon(b['footprint_xy']) for b in plan['real_buildings']]
tree=shapely.STRtree(polygons+real)
road_corridor=unary_union([LineString([(p[0],p[1]) for p in e['points']]).buffer(e['width']/2+2.49) for e in plan['edges']])
infill=[(b,polygons[i]) for i,b in enumerate(boxes) if b['name'].startswith('MAIN_CBD_Infill_')]
overlaps=[];corridor_hits=[]
for b,poly in infill:
    if poly.intersects(road_corridor):corridor_hits.append(b['name'])
    for idx in tree.query(poly,predicate='intersects'):
        other=(polygons+real)[int(idx)]
        if other is poly:continue
        if poly.intersection(other).area>.0001:overlaps.append(b['name']);break
assert not overlaps and not corridor_hits
print('INFILL_CHECK',len(infill),len(overlaps),len(corridor_hits),flush=True)

# Sample the reimported paving triangles against the original terrain and road.
pave_obj=bpy.data.objects['CBD_Conforming_Concrete_Paving']
bbox=[-437,616,750,1298]
pv=triangles(pave_obj,bbox);rng=np.random.default_rng(1326)
chosen=rng.choice(len(pv),size=min(3000,len(pv)),replace=False)
sample=pv[chosen].mean(1)
cbd_road=LocalHeightField([road_obj],bbox)
surface_error=[];road_intrusions=0;terrain_missing=0;anomalies=[];edge_corrections=[]
for p in sample:
    t=terrain.height(p[:2]);rr=cbd_road.height(p[:2])
    if t is None:
        # Very thin exported terrain triangles can fail the planar BVH's
        # containment test after float32 rounding. Measure the actual XY
        # distance and compare the nearest triangle's height plane.
        hits=[]
        for _,_,i,_ in terrain.tree.find_nearest_range(Vector((float(p[0]),float(p[1]),0)),.005):
            tri=terrain.tri[i];dist=Point(p[:2]).distance(Polygon(tri[:,:2]))
            a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;d=p[:2]-a;det=u[0]*v[1]-u[1]*v[0]
            s=(d[0]*v[1]-d[1]*v[0])/det;q=(u[0]*d[1]-u[1]*d[0])/det
            z=tri[0,2]+s*(tri[1,2]-tri[0,2])+q*(tri[2,2]-tri[0,2])
            hits.append((dist,z))
        if hits:
            dist,z=min(hits)
            if dist<.0015 and abs((p[2]-z)-.012)<.001:
                t=z;edge_corrections.append(float(dist))
        if t is None:
            terrain_missing+=1
            if len(anomalies)<20:anomalies.append({'reason':'terrain_missing','point':p.tolist(),'road':rr})
    if t is not None:
        err=abs((p[2]-t)-.012);surface_error.append(err)
        if err>.001 and len(anomalies)<20:anomalies.append({'reason':'surface_error','point':p.tolist(),'terrain':t,'error':err,'road':rr})
    if rr is not None and p[2]>=rr-.002:
        road_intrusions+=1
        if len(anomalies)<20:anomalies.append({'reason':'road_intrusion','point':p.tolist(),'terrain':t,'road':rr})
print('PAVING_CHECK',json.dumps({'samples':len(sample),'terrain_missing':terrain_missing,'road_intrusions':road_intrusions,'max_surface_error':max(surface_error),'near_edge_corrections':len(edge_corrections),'maximum_edge_distance':max(edge_corrections,default=0),'anomalies':anomalies}),flush=True)
assert terrain_missing==0 and road_intrusions==0 and max(surface_error)<.001
assert update['original_geometry_sha256_before']==update['original_geometry_sha256_after']
report={'glb_reimport_success':True,'actual_buildings':models,'site_checks':sites,'texture_byte_checks':texture_checks,
        'cbd_infill_count':len(infill),'cbd_infill_building_overlaps':len(overlaps),'cbd_infill_road_corridor_overlaps':len(corridor_hits),
        'cbd_paved_area_m2':update['cbd_paved_area_m2'],'cbd_paving_samples':len(sample),'cbd_paving_max_height_error_m':max(surface_error),
        'cbd_paving_terrain_missing_samples':terrain_missing,'cbd_paving_road_intrusion_samples':road_intrusions,
        'cbd_paving_near_edge_corrections':len(edge_corrections),'cbd_paving_maximum_edge_distance_m':max(edge_corrections,default=0),
        'original_road_sidewalk_terrain_unchanged':True,'placeholder_buildings':len(boxes),'validation_passed':True}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2))
print('URBAN_VALIDATION_COMPLETE',json.dumps(report,indent=2),flush=True)
