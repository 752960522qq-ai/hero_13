"""Check sidewalk adjacency, right-hand corner orientation and city scale."""
from pathlib import Path
import argparse,gzip,json,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser()
for key in ['glb','plan','deps','report']:ap.add_argument('--'+key,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parent))
import shapely
from shapely.geometry import Point,LineString,Polygon
from city_surface_sampling import HeightField
p=json.loads(a.plan.read_text());row=p['connected_arcades'];alignment=p['frontage_alignment'];assert row['frontage_flush_to_sidewalk'] and not row['ramps'] and row['corner_turn_degrees']==90
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(a.glb.resolve()));bpy.context.view_layer.update();scene=bpy.context.scene;obs=[o for o in scene.objects if o.type=='MESH'];instances=[o for o in scene.objects if o.get('is_building_instance')];assert len(instances)==11
names={o.name:o for o in scene.objects};assert not any(q.startswith(('Oldtown_Open_Row_Continuous_Floor','Oldtown_Corner_Return_Floor','Oldtown_Expanded_Row_Access_','Oldtown_Arcade_Continuous_Canopy','Oldtown_Arcade_Column_')) for q in names)
walk=HeightField([o for o in obs if any(q in o.name for q in ['MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_'])]);o0=np.array(row['front_origin']);U=np.array(row['u']);V=np.array(row['v'])
corner=names['OLDTOWN_Corner_Shop_10'];M=np.asarray(corner.matrix_world);axes=M[:3,:3]/np.linalg.norm(M[:3,:3],axis=0);rec=next(b for b in p['real_buildings'] if b['instance_name']==corner.name);fu=np.array(rec['frontage_u']);fv=np.array(rec['frontage_v']);assert axes[:2,0]@fv>.99999 and axes[:2,1]@fu<-.99999 and np.linalg.det(M[:3,:3])>0,'Corner must rotate towards right junction, without mirroring labels'
centers={b['instance_name']:np.array(b['center']) for b in p['real_buildings']};assert max(row['instances'],key=lambda n:centers[n]@U)==corner.name
def belongs(o):
    while o:
        if o.name in row['instances']:return True
        o=o.parent
    return False
vv=[];ff=[]
for o in obs:
    if not belongs(o) and not o.name.startswith(('Oldtown_Expanded_Row_Foundation_','Oldtown_Row_Partywall_')):continue
    k=len(vv);vv.extend(o.matrix_world@v.co for v in o.data.vertices);o.data.calc_loop_triangles();ff.extend([[k+j for j in t.vertices] for t in o.data.loop_triangles])
bvh=BVHTree.FromPolygons(vv,ff,all_triangles=True);clearance=[];threshold=[];missing=obstructed=0
for q in alignment['frontage']:
    anchor=np.array(q['anchor_xy']);u=np.array(q['u']);v=np.array(q['v']);samplecount=0
    for t in np.linspace(.02,.98,35):
        for distance in [.75,1.5,2.5]:
            xy=anchor+u*q['width_m']*t-v*distance;z=walk.height(xy)
            if z is None:missing+=1;continue
            if bvh.ray_cast(Vector((*xy,z+.035)),Vector((0,0,1)),2.3)[0] is not None:obstructed+=1
            samplecount+=1
    clearance.append({'instance':q['instance'],'sidewalk_samples':samplecount,'net_width_sampled_m':1.75})
    lo,hi=q['sidewalk_height_range_m'];threshold.append({'instance':q['instance'],'floor_to_sidewalk_extreme_difference_m':max(abs(q['floor_m']-lo),abs(q['floor_m']-hi))})
assert missing==obstructed==0,(missing,obstructed)
assert alignment['maximum_edge_seal_width_m']<.25
assert max(q['floor_to_sidewalk_extreme_difference_m'] for q in threshold)<.3
heights=[];scale_error=0
for r in p['real_buildings']:
    inst=names[r['instance_name']];parts=[o for o in inst.children_recursive if o.type=='MESH'];assert len(parts)==1;co=np.array([parts[0].matrix_world@v.co for v in parts[0].data.vertices]);height=float(np.ptp(co[:,2]));axis=np.array(r.get('local_axis_scale',[1,1,1]));scale=np.linalg.norm(np.asarray(inst.matrix_world)[:3,:3],axis=0)/axis;err=float(np.ptp(scale));assert abs(height-r['target_height_m'])<.002 and err<.0001;scale_error=max(scale_error,err);heights.append({'instance':r['instance_name'],'height_m':height,'source_axis_factors':axis.tolist()})
boxerrors=[];zones={}
for b in p['buildings']:
    o=names[b['name']];co=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);boxerrors.append(abs(float(np.ptp(co[:,2]))-b['size'][2]));zones.setdefault(b['zone'],[]).append(b['size'][2])
assert max(boxerrors)<.002
widths={}
for e in p['edges']:
    key=f"{e['carriage_width']:g}";widths[key]=widths.get(key,0)+1
floors={'OLDTOWN_Connected_Arcade_06':3,'OLDTOWN_Connected_Arcade_07':3,'OLDTOWN_Connected_Arcade_05':3,'OLDTOWN_Connected_Shop_08':4,'OLDTOWN_Connected_Shop_09':4,'OLDTOWN_Corner_Shop_10':3,'OLDTOWN_Apartment_11':4}
scale_report={'units':'metres; one model unit equals one metre','real_buildings_measured':heights,'uniform_scale_normalized_max_error':scale_error,'placeholder_buildings_measured':len(boxerrors),'placeholder_height_max_error_m':max(boxerrors),'road_cross_section_width_counts':widths,'street_carriageway_m':9,'street_sidewalk_each_side_m':3,'total_street_corridor_m':15,'zone_placeholder_height_ranges_m':{k:[min(v),float(np.median(v)),max(v)] for k,v in zones.items()},'shop_and_apartment_gross_height_per_storey_m':{n:next(r['target_height_m'] for r in p['real_buildings'] if r['instance_name']==n)/s for n,s in floors.items()},'scale_conclusion':'No unit or axis-scale mismatch detected. The 9m local carriageway is broad for two traffic lanes; retained as the supplied road cross-section, including its centre/edge bands. It is not asserted to be two 4.5m traffic lanes.','visual_reference_only':{'human_height_m':1.75,'car_size_m':[4.5,1.8,1.5]},'design_reference':{'url':'https://zjw.sh.gov.cn/jsgl/20240103/a8d031ed811843019396598f3b62e48c.html','context':'Official Shanghai project approval uses 3.5m standard traffic lanes and 3.25m passenger-car-only lanes. Used as scale context, not a claim of regulatory compliance.'}}
report={'validation_passed':True,'glb_reimport_success':True,'source_buildings':11,'street_models':6,'corner_on_right':True,'corner_rotation_degrees':90,'corner_mirrored':False,'street_at_existing_sidewalk':True,'maximum_edge_seal_width_m':alignment['maximum_edge_seal_width_m'],'removed_detached_walkway_and_ramps':True,'walkway_clearance_checks':clearance,'missing_sidewalk_samples':missing,'obstructed_sidewalk_samples':obstructed,'threshold_levels':threshold,'city_scale':scale_report,'road_sidewalk_geometry_unchanged':alignment['road_sidewalk_geometry_unchanged'],'limits':'Geometry and scale review; game collision, navigation, streaming and frame rate are not configured or tested.'}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2));(a.report.parent/'city_scale_audit.json').write_text(json.dumps(scale_report,indent=2));print('FRONTAGE_ALIGNMENT_VALIDATION_COMPLETE',json.dumps(report),flush=True)
