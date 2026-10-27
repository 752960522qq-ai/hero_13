"""Check the exported row's continuous floor, covered clearance and entries."""
from pathlib import Path
import argparse,gzip,json,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--report',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon,LineString
sys.path.insert(0,str(Path(__file__).resolve().parent));from city_surface_sampling import HeightField
p=json.loads(a.plan.read_text());row=p['connected_arcades'];raw=a.scheme.read_bytes();scheme=json.loads(gzip.decompress(raw) if a.scheme.suffix=='.gz' else raw);road=shapely.from_geojson(scheme['new_pavement']);full=shapely.from_geojson(scheme['new_full_footprint'])
pad=Polygon(row['pad_rectangle']);assert pad.intersection(full).area<.0001
for b in p['buildings']:assert pad.intersection(Polygon(b['footprint'])).area<.0001,b['name']
for b in p['real_buildings']:
    if b['instance_name'] not in row['instances']:assert pad.intersection(Polygon(b['footprint_xy'])).area<.0001
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(a.glb.resolve()));bpy.context.view_layer.update();objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
origin=np.array(row['front_origin']);u=np.array(row['u']);v=np.array(row['v']);z=row['foundation_top_m'];xmin,xmax=row['local_x_range']
def point(x,y,h):return np.r_[origin+u*x+v*y,z+h]
def local_objects(prefixes,bounds):
    out=[]
    for o in objs:
        if not any(o.name.startswith(s) for s in prefixes):continue
        bb=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);lo=bb[:,:2].min(0);hi=bb[:,:2].max(0)
        if hi[0]>=bounds[0] and lo[0]<=bounds[2] and hi[1]>=bounds[1] and lo[1]<=bounds[3]:out.append(o)
    return out
floor=HeightField([bpy.data.objects['Oldtown_Arcade_Continuous_Floor']]);floor_checks=0;maxfloor=0
for x in np.linspace(xmin+.3,xmax-.3,100):
    for y in np.linspace(-2.95,-.35,7):
        xy=point(x,y,0)[:2];height=floor.height(xy);assert height is not None;maxfloor=max(maxfloor,abs(height-z-.004));floor_checks+=1
assert maxfloor<.001
obstacles=[o for o in objs if o.name.startswith(('OLDTOWN_Connected_Arcade_','Oldtown_Arcade_Column_','Oldtown_Arcade_Continuous_Canopy','Oldtown_Arcade_Canopy_Fascia','Oldtown_Arcade_Shared_Wall_'))]
vertices=[];faces=[]
for o in obstacles:
    offset=len(vertices);vertices.extend(o.matrix_world@q.co for q in o.data.vertices);o.data.calc_loop_triangles();faces.extend([[offset+i for i in t.vertices] for t in o.data.loop_triangles])
bvh=BVHTree.FromPolygons(vertices,faces,all_triangles=True)
clearance_rays=0
for y in np.linspace(-2.95,-.35,13):
    for h in [.15,.5,1.0,1.7,2.3,2.6]:
        start=point(xmin+.2,y,h);hit=bvh.ray_cast(Vector(start),Vector((*u,0)),xmax-xmin-.4)[0];assert hit is None,('corridor obstructed',y,h,list(hit) if hit else None);clearance_rays+=1
roof_clearances=[]
for x in np.linspace(xmin+.4,xmax-.4,40):
    for y in [-2.7,-1.65,-.6]:
        start=point(x,y,.05);hit=bvh.ray_cast(Vector(start),Vector((0,0,1)),6)[0];assert hit is not None;head=float(hit.z-z);assert head>=3.65;roof_clearances.append(head)
padbounds=pad.bounds;land=HeightField(local_objects(['MAIN_Sculpted_Terrain_Cell_','Junction_Repairs_Ground_Infill'],[padbounds[0]-2,padbounds[1]-2,padbounds[2]+2,padbounds[3]+2]));heights=[]
for t in land.tri:
    xy=shapely.get_coordinates(Polygon(t[:,:2]).intersection(pad))
    if not len(xy):continue
    aa=t[0,:2];b=t[1,:2]-aa;c=t[2,:2]-aa;d=xy-aa;det=b[0]*c[1]-b[1]*c[0];s=(d[:,0]*c[1]-d[:,1]*c[0])/det;q=(b[0]*d[:,1]-b[1]*d[:,0])/det;heights.extend((t[0,2]+s*(t[1,2]-t[0,2])+q*(t[2,2]-t[0,2])).tolist())
assert heights and z-max(heights)>.015
ramps=[]
for r in row['ramps']:
    start=np.array(r['start_xy']);end=np.array(r['end_xy']);vec=end-start;L=np.linalg.norm(vec);tangent=vec/L;normal=np.array([-tangent[1],tangent[0]]);poly=LineString([start,end]).buffer(1,cap_style='flat');assert poly.intersection(road).area<.001
    b=poly.bounds;bounds=[b[0]-3,b[1]-3,b[2]+3,b[3]+3];rf=HeightField([bpy.data.objects[r['name']]]);tf=HeightField(local_objects(['MAIN_Sculpted_Terrain_Cell_','Junction_Repairs_Ground_Infill'],bounds));wf=HeightField(local_objects(['MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_'],bounds))
    buried=0;missing=0;obstructions=0;count=0
    for s in np.linspace(.05,L-.05,21):
        for k in [-.8,0,.8]:
            xy=start+tangent*s+normal*k;rz=rf.height(xy);tz=tf.height(xy);count+=1
            if rz is None:missing+=1;continue
            if tz is not None and tz>rz+.008:buried+=1
            hit=bvh.ray_cast(Vector((*xy,rz+.08)),Vector((0,0,1)),2.3)[0]
            if hit is not None:obstructions+=1
    joins=[]
    for k in [-.8,0,.8]:
        xy=end-tangent*.02+normal*k;rz=rf.height(xy);wz=wf.height(xy);assert rz is not None and wz is not None;joins.append(abs(rz-wz))
    assert missing==buried==obstructions==0 and max(joins)<.02
    ramps.append({'name':r['name'],'surface_samples':count,'missing':missing,'terrain_penetrations':buried,'head_obstructions':obstructions,'sidewalk_join_gap_m':max(joins),'maximum_grade':r['maximum_grade']})
for seam in row['seams']:assert seam['core_wall_overlap_m']>.025 and seam['core_wall_overlap_m']<.06
report={'glb_reimport_success':True,'connected_source_models':len(row['instances']),'row_length_m':row['length_m'],'shared_floor_samples':floor_checks,'shared_floor_max_height_error_m':maxfloor,'clear_corridor_width_m':2.6,'corridor_horizontal_rays':clearance_rays,'corridor_obstructions':0,'minimum_covered_headroom_m':min(roof_clearances),'foundation_top_above_terrain_m':z-max(heights),'sidewalk_ramps':ramps,'party_wall_seams':row['seams'],'validation_passed':True,'limits':'Geometric inspection; game collisions and navigation have not been configured.'}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2));print('ARCADE_VALIDATION_COMPLETE',json.dumps(report),flush=True)
