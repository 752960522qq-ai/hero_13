"""Reimport and sample the final GLB, including actual junction surfaces."""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser()
ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--baseline-glb',type=Path,required=True)
ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--districts',type=Path,required=True)
ap.add_argument('--chunk-report',type=Path,required=True);ap.add_argument('--source',type=Path,action='append',required=True)
ap.add_argument('--shapely-path',type=Path);ap.add_argument('--report',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Point,Polygon,LineString,box
from scipy.spatial import cKDTree
plan=json.loads(args.plan.read_text());scheme=json.loads(args.scheme.read_text());districts=json.loads(args.districts.read_text())
chunk_report=json.loads(args.chunk_report.read_text());roadshape=shapely.from_geojson(scheme['new_pavement'])
walkshape=shapely.from_geojson(scheme['new_full_footprint']).difference(roadshape).buffer(-.025)
def glb_images(path):
    with path.open('rb') as f:
        magic,version,total,n,kind=struct.unpack('<4sIIII',f.read(20));assert magic==b'glTF' and version==2
        meta=json.loads(f.read(n));length,kind=struct.unpack('<II',f.read(8));blob=f.read(length)
    imgs=[]
    for im in meta.get('images',[]):
        if 'bufferView' in im:
            bv=meta['bufferViews'][im['bufferView']];offset=bv.get('byteOffset',0)
            imgs.append(hashlib.sha256(blob[offset:offset+bv['byteLength']]).hexdigest())
    return meta,imgs
meta,images=glb_images(args.glb);_,old_images=glb_images(args.baseline_glb)
assert sorted(images)==sorted(old_images),'An existing source atlas or texture was altered'
textures=[]
for file in args.source:
    _,source=glb_images(file);counts=[images.count(x) for x in source];assert source and all(c==1 for c in counts)
    textures.append({'source':file.name,'matching_original_image_bytes':counts})
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()));bpy.context.view_layer.update()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
def below(o,name):
    while o:
        if o.name==name:return True
        o=o.parent
    return False
def field_triangles(obj,bounds):
    # Most chunks lie far from a given repair site; avoid reading their geometry.
    bbox=np.array([obj.matrix_world@Vector(c) for c in obj.bound_box]);lo=bbox[:,:2].min(0);hi=bbox[:,:2].max(0)
    xmin,ymin,xmax,ymax=bounds
    if hi[0]<xmin or lo[0]>xmax or hi[1]<ymin or lo[1]>ymax:return np.empty((0,3,3))
    m=obj.data;m.calc_loop_triangles()
    co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(np.float64)
    matrix=np.asarray(obj.matrix_world,np.float64);co=co@matrix[:3,:3].T+matrix[:3,3]
    ids=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',ids);tri=co[ids.reshape(-1,3)]
    low=tri[:,:,:2].min(1);high=tri[:,:,:2].max(1)
    tri=tri[(high[:,0]>=xmin)&(low[:,0]<=xmax)&(high[:,1]>=ymin)&(low[:,1]<=ymax)]
    u=tri[:,1,:2]-tri[:,0,:2];v=tri[:,2,:2]-tri[:,0,:2]
    return tri[(u[:,0]*v[:,1]-u[:,1]*v[:,0])>1e-8]
class Field:
    def __init__(self,objs,bounds):
        parts=[q for o in objs if len(q:=field_triangles(o,bounds))]
        if not parts:raise ValueError('empty sampled surface')
        self.tri=np.concatenate(parts);xy=self.tri[:,:,:2].reshape(-1,2);unique,ids=np.unique(xy,axis=0,return_inverse=True)
        self.bvh=BVHTree.FromPolygons(np.c_[unique,np.zeros(len(unique))].tolist(),ids.reshape(-1,3).tolist(),all_triangles=True)
    def height(self,xy):
        xy=np.asarray(xy[:2],np.float64);values=[]
        for _,_,i,_ in self.bvh.find_nearest_range(Vector((float(xy[0]),float(xy[1]),0)),.002):
            t=self.tri[i];a=t[0,:2];u=t[1,:2]-a;v=t[2,:2]-a;d=xy-a;det=u[0]*v[1]-u[1]*v[0]
            s=(d[0]*v[1]-d[1]*v[0])/det;q=(u[0]*d[1]-u[1]*d[0])/det
            if min(1-s-q,s,q)>=-1e-7:values.append((1-s-q)*t[0,2]+s*t[1,2]+q*t[2,2])
        return None if not values else float(max(values))
def prefix(o,names):return any(o.name.startswith(x+'_Cell_') or o.name==x for x in names)
roads=[o for o in objects if prefix(o,['MAIN_Road_Modular_Repaired','Continuous_Pavement_Repaired','Junction_Repairs_Asphalt','Junction_Repairs_Original_Road_Kit'])]
walks=[o for o in objects if prefix(o,['MAIN_Sidewalk_Modular_Continuous','Sidewalk_Continuous_Transition_Base','Junction_Repairs_Sidewalk_OriginalAtlas'])]
lands=[o for o in objects if prefix(o,['MAIN_Sculpted_Terrain','Junction_Repairs_Ground_Infill'])]
assert roads and walks and lands
instances=[o for o in bpy.context.scene.objects if o.get('is_building_instance')]
assert len(instances)==4 and len({x.name for x in instances})==4
model_results=[]
for r in plan['real_buildings']:
    inst=next(x for x in instances if x.name==r['instance_name']);parts=[o for o in objects if below(o,inst.name)]
    assert len(parts)==1 and parts[0].data.uv_layers.active
    co=np.empty(len(parts[0].data.vertices)*3,np.float32);parts[0].data.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    world=np.asarray(parts[0].matrix_world,np.float64);co=co@world[:3,:3].T+world[:3,3]
    height=float(co[:,2].max()-co[:,2].min());scales=np.linalg.norm(np.asarray(inst.matrix_world)[:3,:3],axis=0)
    error=float(scales.max()-scales.min())
    assert abs(height-r['target_height_m'])<.002 and error<.0001
    model_results.append({'name':inst.name,'height_m':height,'uniform_scale_error':error})
print('MODEL_REIMPORT',json.dumps(model_results),flush=True)

repairs=[]
for fix in scheme['repairs']:
    bounds=fix['patch_bounds'];bounds=[bounds[0]-3,bounds[1]-3,bounds[2]+3,bounds[3]+3]
    rf=Field(roads,bounds);wf=Field(walks,bounds);tf=Field(lands,bounds)
    target=np.asarray(fix['node_xy']);nid=min(range(len(plan['nodes'])),key=lambda i:np.linalg.norm(np.asarray(plan['nodes'][i]['xy'])-target))
    candidates=[plan['edges'][i] for i in plan['nodes'][nid]['edges'] if plan['edges'][i]['name']==fix['edge']]
    edge=max(candidates,key=lambda e:e['length'])
    q=np.asarray(edge['points'])
    if edge['b']==nid:q=q[::-1]
    ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
    n=0;missing=0;buried=0;max_delta=0;walk_n=0;walk_missing=0;walk_buried=0;offenders=[]
    for dist in np.arange(2,min(80,ds[-1]-1),2):
        pos=np.array([np.interp(dist,ds,q[:,i]) for i in range(3)])
        lo=np.array([np.interp(max(0,dist-.5),ds,q[:,i]) for i in range(2)])
        hi=np.array([np.interp(min(ds[-1],dist+.5),ds,q[:,i]) for i in range(2)])
        tangent=hi-lo;tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
        for side in [-1,1]:
            xy=pos[:2]+normal*side*edge['carriage_width']*.27
            if not roadshape.buffer(-.05).covers(Point(xy)):continue
            n+=1;z=rf.height(xy);land=tf.height(xy)
            if z is None:
                missing+=1
                if len(offenders)<8:offenders.append({'xy':xy.tolist(),'kind':'road_missing'})
                continue
            max_delta=max(max_delta,abs(z-pos[2]))
            if land is not None and land>z+.005:
                buried+=1
                if len(offenders)<8:offenders.append({'xy':xy.tolist(),'kind':'road_buried','road':z,'terrain':land})
            xy=pos[:2]+normal*side*(edge['carriage_width']/2+1.5)
            if not walkshape.covers(Point(xy)):continue
            walk_n+=1;w=wf.height(xy);land=tf.height(xy)
            if w is None:walk_missing+=1
            elif land is not None and land>w+.005:walk_buried+=1
    result={'edge':fix['edge'],'road_samples':n,'road_missing':missing,'road_buried':buried,
            'road_max_surface_centerline_delta_m':max_delta,'sidewalk_samples':walk_n,'sidewalk_missing':walk_missing,
            'sidewalk_terrain_penetrations':walk_buried,'details':offenders}
    repairs.append(result);print('ROAD_SURFACE_CHECK',json.dumps(result),flush=True)
    assert n>=25 and missing==buried==walk_missing==walk_buried==0

# Foundation footprint extrema are derived from triangle clipping rather than
# a sparse grid; this catches sloping corners between terrain samples.
foundation_checks=[]
for yard in districts['east_container_yards']:
    poly=Polygon(yard['footprint']);b=poly.bounds
    east=[o for o in objects if prefix(o,['EAST_Sculpted_Terrain'])]
    terrain=Field(east,[b[0]-1,b[1]-1,b[2]+1,b[3]+1])
    zvals=[];tris=terrain.tri
    for tri in tris:
        cut=Polygon(tri[:,:2]).intersection(poly);xy=shapely.get_coordinates(cut)
        if not len(xy):continue
        a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;dd=xy-a;det=u[0]*v[1]-u[1]*v[0]
        s=(dd[:,0]*v[1]-dd[:,1]*v[0])/det;t=(u[0]*dd[:,1]-u[1]*dd[:,0])/det
        zvals.extend((tri[0,2]+s*(tri[1,2]-tri[0,2])+t*(tri[2,2]-tri[0,2])).tolist())
    assert zvals
    clearance=yard['foundation_top_m']-max(zvals)
    record={'name':yard['name'],'pad_top_above_max_terrain_m':clearance};foundation_checks.append(record)
    print('YARD_FOUNDATION_CHECK',json.dumps(record),flush=True)
    assert clearance>=.015

eastroads=[o for o in objects if prefix(o,['EAST_Road_Modular_Repaired','Continuous_Pavement_Repaired'])]
eastwalks=[o for o in objects if prefix(o,['EAST_Sidewalk_Modular_Continuous','Sidewalk_Continuous_Transition_Base'])]
eastland=[o for o in objects if prefix(o,['EAST_Sculpted_Terrain'])]
port_checks=[]
for i,access in enumerate(plan['port_service_access']):
    start=np.asarray(access['start_xy']);end=np.asarray(access['end_xy']);u=end-start;length=np.linalg.norm(u);u/=length
    normal=np.array([-u[1],u[0]]);lo=np.minimum(start,end)-8;hi=np.maximum(start,end)+8
    bounds=[lo[0],lo[1],hi[0],hi[1]]
    drive=next(o for o in objects if o.name==f'Port_Service_Drive_{i:02d}')
    df=Field([drive],bounds);tf=Field(eastland,bounds);rf=Field(eastroads,bounds);wf=Field(eastwalks,bounds)
    missing=buried=0;samples=0
    for station in np.linspace(.5,length-.5,21):
        for offset in [-2.5,0,2.5]:
            xy=start+u*station+normal*offset;z=df.height(xy);ground=tf.height(xy);samples+=1
            if z is None:missing+=1
            elif ground is not None and ground>z+.008:buried+=1
    road_deltas=[]
    for offset in [-2,0,2]:
        xy=end-u*.03+normal*offset;z=df.height(xy);r=rf.height(xy)
        if z is not None and r is not None:road_deltas.append(abs(z-r))
    walk_deltas=[];center=np.asarray(access['walk_center_xy'])
    for side in [-1,1]:
        inside=center+normal*side*2.98;outside=center+normal*side*3.02
        z=df.height(inside);w=wf.height(outside)
        if z is not None and w is not None:walk_deltas.append(abs(z-w))
    corridor=LineString([start,end]).buffer(3,cap_style='flat');container_hits=[]
    for obj in objects:
        if not obj.name.startswith(access['yard']+'_Container_'):continue
        bb=np.array([obj.matrix_world@Vector(c) for c in obj.bound_box]);poly=box(bb[:,0].min(),bb[:,1].min(),bb[:,0].max(),bb[:,1].max())
        if corridor.intersection(poly).area>.001:container_hits.append(obj.name)
    record={'yard':access['yard'],'surface_samples':samples,'missing':missing,'terrain_penetrations':buried,
            'road_join_samples':len(road_deltas),'road_join_max_gap_m':max(road_deltas,default=None),
            'sidewalk_join_samples':len(walk_deltas),'sidewalk_join_max_gap_m':max(walk_deltas,default=None),
            'container_obstructions':container_hits}
    print('PORT_ACCESS_SURFACE_CHECK',json.dumps(record),flush=True);port_checks.append(record)
    assert missing==buried==0 and len(road_deltas)>=2 and max(road_deltas)<.025
    assert len(walk_deltas)==2 and max(walk_deltas)<.035 and not container_hits

for info in chunk_report:
    actual=[o for o in objects if o.name.startswith(info['source']+'_Cell_')]
    count=sum(len(o.data.polygons) for o in actual)
    assert len(actual)==info['cell_count'] and count==info['triangles_after'],(info['source'],len(actual),count)
result={'glb_reimport_success':True,'original_images_unchanged':True,'source_texture_checks':textures,'real_buildings':model_results,
 'road_surface_checks':repairs,'yard_foundation_checks':foundation_checks,'port_access_surface_checks':port_checks,'streaming_meshes_checked':len(chunk_report),
 'streaming_chunks_checked':sum(x['cell_count'] for x in chunk_report),'validation_passed':True}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2))
print('REDEVELOPMENT_VALIDATION_COMPLETE',json.dumps(result,indent=2),flush=True)
