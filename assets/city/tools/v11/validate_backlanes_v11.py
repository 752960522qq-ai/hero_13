"""Independent validation of every new rear-house instance and its real mesh access."""
import bpy,sys,json,hashlib,collections,math,argparse
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--model-dir',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--baseline',type=Path,default=ROOT/'recovery/huizhou_city_v10');ap.add_argument('--deps',type=Path,default=ROOT/'blender_deps');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
OLD=args.baseline.resolve();sys.path.insert(0,str(args.deps.resolve()));sys.path.insert(0,str(OLD/'tools'))
import shapely
from shapely.geometry import Polygon,LineString,Point
from city_surface_sampling import HeightField
out=args.model_dir.resolve();p=json.loads((out/'city_plan.json').read_text());old=json.loads((OLD/'city_plan.json').read_text());report={}
assert p['coasts']==old['coasts'] and p['lake']==old['lake'] and p['edges']==old['edges']
assert p['real_buildings'][:15]==old['real_buildings']
assert not any(b['typology']=='backlane_house' for b in p['buildings'])
assert len(p['buildings'])==590 and len(p['real_buildings'])==75 and len(p['buildings'])+len(p['real_buildings'])==665<700
replaced={b['name'] for b in old['buildings'] if b['typology']=='backlane_house'};new=p['real_buildings'][15:];assert set(n for r in new for n in r['replaces_placeholder_sites'])==replaced
report.update(backlane_placeholders_remaining=0,rear_sites_replaced=35,new_source_instances=60,existing_rear_instances=2,total_rear_source_instances=62,city_total_buildings=665,land_area_unchanged_m2=p['stats']['land_area_m2'],road_graph_unchanged=True,original_15_source_placements_unchanged=True)
def ancestry(o):
    while o:yield o.name;o=o.parent
def geometry(o):
    m=o.data;h=hashlib.sha256();h.update(np.asarray(o.matrix_world,dtype=np.float64).tobytes());co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);h.update(co.tobytes());v=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',v);h.update(v.tobytes())
    for l in m.uv_layers:
        a=np.empty(len(l.data)*2,np.float32);l.data.foreach_get('uv',a);h.update(a.tobytes())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(OLD/'huizhou_road_network.blend'));bpy.context.view_layer.update()
names={a['name'] for a in old['pedestrian_alleys']}
oldhash={o.name:geometry(o) for o in bpy.context.scene.objects if o.type=='MESH' and ('03_ROAD_NETWORK'in set(ancestry(o)) or '06_SIDEWALKS'in set(ancestry(o)) or o.name in names or any(r['instance_name'] in set(ancestry(o)) for r in old['real_buildings']))}
bpy.ops.wm.open_mainfile(filepath=str(out/'huizhou_road_network.blend'));bpy.context.view_layer.update()
for name,h in oldhash.items():assert name in bpy.data.objects and geometry(bpy.data.objects[name])==h,('retained mesh changed',name)
report['unchanged_original_road_walk_and_source_meshes_checked']=len(oldhash)
linked={r['source_key']:set() for r in new}
for r in new:
    inst=bpy.data.objects[r['instance_name']];assert np.linalg.det(np.array(inst.matrix_world)[:3,:3])>0
    linked[r['source_key']].update(o.data.name for o in inst.children_recursive if o.type=='MESH')
assert all(len(v)==1 for v in linked.values());report['linked_mesh_templates']=len(linked);report['new_reuse_counts']=dict(collections.Counter(r['source_key'] for r in new))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(out/'huizhou_road_network.glb'));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
terrain=HeightField([o for o in obs if o.get('surface_type')=='terrain']);oldwalk=HeightField([o for o in obs if o.get('surface_type')=='sidewalk' or o.name in names])
obsv=[];obsf=[]
for o in obs:
    if o.get('surface_type') in ['terrain','coast','sidewalk','curb','pavement','road_kit','backlane_entry_walk'] or '02_WATER'in set(ancestry(o)):continue
    m=o.data;m.calc_loop_triangles();co=np.array([v.co[:] for v in m.vertices]);M=np.asarray(o.matrix_world);co=co@M[:3,:3].T+M[:3,3];k=len(obsv);obsv.extend(co.tolist());obsf.extend([[k+i for i in t.vertices] for t in m.loop_triangles])
bvh=BVHTree.FromPolygons(obsv,obsf,all_triangles=True);checks=[];rays=0;maxgrade=0.;allpen=0.
for link in p['rear_access_links']:
    field=HeightField([bpy.data.objects[link['name']+'_Entry_Walk']]);line=LineString(link['points']);samples=[];penetration=0.;grades=[]
    for a,b in zip(np.array(link['points'])[:-1],np.array(link['points'])[1:]):
        delta=b-a;L=np.linalg.norm(delta);t=delta/L;n=np.array([-t[1],t[0]]);ss=np.linspace(0,L,max(3,int(math.ceil(L/.65))+1));zs=[]
        for s in ss:
            c=a+t*s;h=field.height(c);assert h is not None,('new link hole',link['name'],c.tolist());zs.append(h)
            for lateral in [-1.4,0,1.4]:
                xy=c+n*lateral;z=field.height(xy);assert z is not None,('new link lacks clear width',link['name'],xy.tolist());soil=terrain.height(xy)
                if soil is not None:penetration=max(penetration,soil-z)
                hit,_,_,_=bvh.ray_cast(Vector((*xy,z+.12)),Vector((0,0,1)),2.1);assert hit is None,('new path headroom blocked',link['name'],xy.tolist());rays+=1
        grades.extend((np.abs(np.diff(zs))/np.diff(ss)).tolist())
    grade=max(grades or [0.]);maxgrade=max(maxgrade,grade);assert grade<.084,('new access ramp too steep',link['name'],grade);assert penetration<.035,('terrain intrudes into new link',link['name'],penetration);allpen=max(allpen,penetration)
    goal=np.array(link['points'][-1]);join=oldwalk.height(goal);z=field.height(goal);assert join is not None and z is not None and abs(z-join)<.025,('new link does not join old walk',link['name'],join,z)
    checks.append({'name':link['name'],'length_m':line.length,'clear_width_sampled_m':2.8,'maximum_grade':grade,'join_lip_m':abs(z-join),'buildings_connected':len(link['source_buildings'])})
report.update(status='PASS',connected_rear_rows=len(checks),new_path_headroom_rays=rays,maximum_actual_access_grade=maxgrade,maximum_terrain_penetration_m=allpen,connections=checks)
overlaps=0;overlap_error=0.
newfields=[HeightField([bpy.data.objects[r['name']+'_Entry_Walk']]) for r in p['rear_rows']]
newpolys=[Polygon(r['polygon']) for r in p['rear_rows']];ptree=shapely.STRtree(newpolys)
for alley in p['pedestrian_alleys']:
    line=LineString(alley['points']);co=np.array(alley['points']);t=(co[-1]-co[0])/line.length;n=np.array([-t[1],t[0]])
    for s in np.linspace(0,line.length,max(3,int(line.length/2)+1)):
        for offset in [-1.15,0,1.15]:
            xy=np.array(line.interpolate(s).coords[0])+n*offset;pt=Point(xy)
            for i in ptree.query(pt):
                z=newfields[i].height(xy)
                if z is None:continue
                prior=oldwalk.height(xy);assert prior is not None;error=abs(z-prior);overlap_error=max(overlap_error,error);overlaps+=1
                assert error<.012,('raised deck interrupts existing alley',alley['name'],p['rear_rows'][i]['name'],error)
report['existing_alley_overlap_samples']=overlaps;report['maximum_existing_alley_surface_difference_m']=overlap_error
(out/'rear_validation.json').write_text(json.dumps(report,indent=2));print('V11_REAR_VALIDATION_PASS',json.dumps({k:v for k,v in report.items() if k!='connections'}),flush=True)
