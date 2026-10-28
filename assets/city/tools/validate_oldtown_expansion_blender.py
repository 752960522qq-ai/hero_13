"""Validate the open street, enlarged corner facade and apartment access."""
from pathlib import Path
import argparse,gzip,json,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
from shapely.geometry import Polygon,LineString
import shapely
sys.path.insert(0,str(Path(__file__).resolve().parent));from city_surface_sampling import HeightField
p=json.loads(a.plan.read_text());row=p['connected_arcades'];scheme=json.loads(gzip.decompress(a.scheme.read_bytes()));road=shapely.from_geojson(scheme['new_pavement']);full=shapely.from_geojson(scheme['new_full_footprint']);pad=Polygon(row['pad_rectangle']);apt=p['oldtown_expansion']['apartment']
assert pad.intersection(full).area<.0001
for b in p['buildings']:assert pad.intersection(Polygon(b['footprint'])).area<.0001
for b in p['real_buildings']:
    if b['instance_name'] not in row['instances']:assert pad.intersection(Polygon(b['footprint_xy'])).area<.0001
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(a.glb.resolve()));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert not any(o.name.startswith(('Oldtown_Arcade_Continuous_Canopy','Oldtown_Arcade_Canopy_Fascia','Oldtown_Arcade_Column_')) for o in bpy.context.scene.objects)
instances=[o for o in bpy.context.scene.objects if o.get('is_building_instance')];assert len(instances)==11;corner=next(o for o in instances if o.name==row['corner_instance']);s=np.linalg.norm(np.asarray(corner.matrix_world)[:3,:3],axis=0);assert abs(s[1]/s[0]-1.45)<1e-5 and abs(s[2]/s[0]-1)<1e-5
origin=np.array(row['front_origin']);u=np.array(row['u']);v=np.array(row['v']);top=row['foundation_top_m'];xmin,xmax=row['local_x_range']
def point(x,y,h):return np.r_[origin+u*x+v*y,top+h]
floor=HeightField([bpy.data.objects['Oldtown_Open_Row_Continuous_Floor']]);samples=0;error=0
for x in np.linspace(xmin+.2,xmax-.2,150):
    for y in np.linspace(-3.4,-.8,7):
        h=floor.height(point(x,y,0)[:2]);assert h is not None;error=max(error,abs(h-top-.004));samples+=1
assert error<.001
parts=[o for o in obs if o.name.startswith(('OLDTOWN_Connected_','OLDTOWN_Corner_Shop_10_','Oldtown_Row_Partywall_'))];vv=[];ff=[]
for o in parts:
    k=len(vv);vv.extend(o.matrix_world@q.co for q in o.data.vertices);o.data.calc_loop_triangles();ff.extend([[k+i for i in t.vertices] for t in o.data.loop_triangles])
bvh=BVHTree.FromPolygons(vv,ff,all_triangles=True);rays=0
for y in np.linspace(-3.4,-.8,14):
    for h in [.15,.5,1.0,1.7,2.3]:
        hit=bvh.ray_cast(Vector(point(xmin+.2,y,h)),Vector((*u,0)),xmax-xmin-.4)[0];assert hit is None,('open frontage obstructed',y,h);rays+=1
return_floor=HeightField([bpy.data.objects['Oldtown_Corner_Return_Floor']]);return_samples=0
for x in np.linspace(row['body_max_x']+.15,row['body_max_x']+2.15,7):
    for y in np.linspace(-3.3,row['corner_depth_m']+.1,21):
        h=return_floor.height(point(x,y,0)[:2]);assert h is not None and abs(h-top-.006)<.001;return_samples+=1
def local_objects(prefixes,bounds):
    result=[]
    for o in obs:
        if not any(o.name.startswith(q) for q in prefixes):continue
        bb=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);lo=bb[:,:2].min(0);hi=bb[:,:2].max(0)
        if hi[0]>=bounds[0] and lo[0]<=bounds[2] and hi[1]>=bounds[1] and lo[1]<=bounds[3]:result.append(o)
    return result
allramps=row['ramps']+[{'name':'OLDTOWN_Apartment_11_Sidewalk_Access','start_xy':apt['access_start_xy'],'end_xy':apt['access_end_xy'],'width_m':3.,'maximum_grade':apt['access_maximum_grade']}];ramp_checks=[]
for r in allramps:
    start=np.array(r['start_xy']);end=np.array(r['end_xy']);u0=end-start;L=np.linalg.norm(u0);u0/=L;n=np.array([-u0[1],u0[0]]);g=LineString([start,end]).buffer(r['width_m']/2,cap_style='flat');assert g.intersection(road).area<.001;b=g.bounds;bounds=[b[0]-2,b[1]-2,b[2]+2,b[3]+2];rf=HeightField([bpy.data.objects[r['name']]]);tf=HeightField(local_objects(['MAIN_Sculpted_Terrain_Cell_','Junction_Repairs_Ground_Infill'],bounds));wf=HeightField(local_objects(['MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_'],bounds));buried=missing=0
    for t in np.linspace(.05,L-.05,25):
        for offset in [-r['width_m']*.4,0,r['width_m']*.4]:
            xy=start+u0*t+n*offset;z=rf.height(xy);land=tf.height(xy)
            if z is None:missing+=1
            elif land is not None and land>z+.009:buried+=1
    gaps=[]
    for offset in [-r['width_m']*.4,0,r['width_m']*.4]:
        xy=end-u0*.02+n*offset;rz=rf.height(xy);wz=wf.height(xy);assert rz is not None and wz is not None;gaps.append(abs(rz-wz))
    assert missing==buried==0 and max(gaps)<.02 and r['maximum_grade']<.085;ramp_checks.append({'name':r['name'],'samples':75,'missing':missing,'terrain_penetrations':buried,'sidewalk_join_gap_m':max(gaps),'maximum_grade':r['maximum_grade']})
report={'glb_reimport_success':True,'source_buildings':11,'street_models':6,'street_length_m':row['length_m'],'added_canopy_removed':True,'added_columns_removed':True,'corner_depth_scale':float(s[1]/s[0]),'corner_height_scale_relative_to_width':float(s[2]/s[0]),'open_floor_samples':samples,'open_floor_max_height_error_m':error,'clear_walk_width_m':2.6,'horizontal_clearance_rays':rays,'walk_obstructions':0,'corner_return_floor_samples':return_samples,'ramp_checks':ramp_checks,'validation_passed':True,'limits':'Geometry inspection only; runtime collisions and navigation are not configured.'}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2));print('OLDTOWN_EXPANSION_VALIDATION_COMPLETE',json.dumps(report),flush=True)
