"""Independent native geometry checks for the final v15 scene."""
import bpy,sys,json,math,hashlib,collections
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
from city_surface_sampling import HeightField
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from mathutils import Vector
old=json.load(open('/workspace/scratch/705f52588668/work_v14/model/city_plan.json'));p=json.load(open(ROOT/'model/city_plan.json'));report=json.load(open(ROOT/'model/v15_build_report.json'))
fail=[]
def check(ok,label,details=None):
    if not ok:fail.append({'check':label,'details':details})
def datahash(o):
    h=hashlib.sha256();m=o.data;h.update(np.array([v.co[:] for v in m.vertices],np.float32).tobytes());h.update(np.array([v for f in m.polygons for v in f.vertices],np.int32).tobytes())
    for uv in m.uv_layers:h.update(np.array([v.uv[:] for v in uv.data],np.float32).tobytes())
    h.update(str([m.name for m in m.materials]).encode());return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath='/workspace/scratch/705f52588668/work_v14/model/huizhou_road_network.blend');sc=bpy.context.scene
source_before={o.name:datahash(o) for r in old['real_buildings'] for o in bpy.data.objects[r['instance_name']].children_recursive if o.type=='MESH'}
roads_before={o.name:(datahash(o),np.array(o.matrix_world).tolist()) for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['road','sidewalk','bridge','carriageway'] or any(k in o.name for k in ['Road_','Roads_','IX_A','IX_B','BRIDGES_']))}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/huizhou_road_network.blend'));bpy.context.view_layer.update();sc=bpy.context.scene
for k in ['coasts','lake','nodes','edges','interchanges','pedestrian_alleys']:check(p[k]==old[k],'unchanged_'+k)
check(p['cbd_plan']['tianming']==old['cbd_plan']['tianming'],'tianming_reservation_preserved')
check(len(p['buildings'])==540 and len(p['real_buildings'])==124,'building_count_664')
for name,h in source_before.items():check(name in sc.objects and datahash(sc.objects[name])==h,'source_mesh_texture_scale_unchanged',name)
for name,(h,M) in roads_before.items():check(name in sc.objects and datahash(sc.objects[name])==h and np.array_equal(np.array(sc.objects[name].matrix_world),M),'street_mesh_unchanged',name)
realmap={r['instance_name']:r for r in p['real_buildings']};boxmap={b['name']:b for b in p['buildings']};moved={r['name'] for r in report['moved_buildings']};land=Polygon(p['coasts']['MAIN']);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
allpolys=[(r.get('name',r.get('instance_name')),Polygon(r.get('footprint',r.get('footprint_xy')))) for r in p['buildings']+p['real_buildings']]
roadfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.01) for e in p['edges']]);height_checks=[];space=[]
for name in moved:
    r=realmap.get(name,boxmap.get(name));poly=Polygon(r.get('footprint_xy',r.get('footprint')))
    check(land.covers(poly),'moved_building_on_land',name);check(poly.intersection(reserve).area<.001,'tianming_clear',name);check(poly.intersection(roadfull).area<.001,'moved_building_clear_of_streets',name)
    overlaps=[n for n,q in allpolys if n!=name and poly.intersection(q).area>.01];check(not overlaps,'footprints_do_not_overlap',[name,overlaps])
    if name in realmap:
        inst=bpy.data.objects[name];co=[]
        for o in inst.children_recursive:
            if o.type!='MESH':continue
            M=np.array(o.matrix_world);c=np.array([v.co[:] for v in o.data.vertices]);co.append(c@M[:3,:3].T+M[:3,3])
        co=np.concatenate(co);height=float(co[:,2].max()-co[:,2].min());check(abs(height-r['target_height_m'])<.003,'source_height_preserved',[name,height]);check(np.linalg.det(np.array(inst.matrix_world)[:3,:3])>0,'no_mirror',name)
        floor=r['floor'];foundation=HeightField([bpy.data.objects[name+'_Foundation']]);top=foundation.height(r['center']);gap=float(co[:,2].min()-top);check(-.002<=gap<=.15,'source_base_supported',[name,gap]);height_checks.append({'name':name,'height_m':height,'bottom_to_foundation_m':gap})
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);ground=[]
for r in p['buildings']+p['real_buildings']:
    name=r.get('name',r.get('instance_name'));poly=Polygon(r.get('footprint',r.get('footprint_xy')));floor=r.get('base',r.get('floor'));penetration=0.
    inner=poly.buffer(-.25)
    if inner.is_empty:continue
    xmin,ymin,xmax,ymax=inner.bounds;pts=list(shapely.segmentize(inner.exterior,1.5).coords)
    for x in np.arange(xmin,xmax,2.5):
        for y in np.arange(ymin,ymax,2.5):
            if inner.covers(Point(x,y)):pts.append((x,y))
    for q in pts:
        h=soil.height(q)
        if h is not None:penetration=max(penetration,h-floor)
    check(penetration<=.081,'terrain_clear_of_building_floor',[name,penetration]);ground.append({'name':name,'terrain_penetration_m':penetration})
walk_checks=[]
for w in p['access_v15']:
    ob=bpy.data.objects.get(w['name']);check(ob is not None,'site_access_present',w['name'])
    if ob is None:continue
    field=HeightField([ob]);route=LineString(w['route']);holes=[];penetration=0.;zs=[]
    for d in np.linspace(0,route.length,max(4,int(route.length/.3)+1)):
        xy=np.array(route.interpolate(d).coords[0]);aa=np.array(route.interpolate(max(0,d-.04)).coords[0]);bb=np.array(route.interpolate(min(route.length,d+.04)).coords[0]);u=bb-aa;u/=max(1e-8,np.linalg.norm(u));n=np.array([-u[1],u[0]])
        for off in [0,-1.,1.]:
            q=xy+n*off;z=field.height(q)
            if z is None:holes.append(q.tolist());continue
            h=soil.height(q)
            if h is not None:penetration=max(penetration,h-z)
            if off==0:zs.append([d,z])
    check(not holes,'access_surface_continuous',[w['name'],holes[:8],len(holes)]);check(penetration<=.04,'terrain_clear_of_access',[w['name'],penetration])
    if w['stairs']:check(w['riser_height_m']<=.175 and w['tread_run_m']>=.30,'stair_dimensions',[w['name'],w['riser_height_m'],w['tread_run_m']])
    else:
        grade=max([abs(z1-z0)/max(.0001,d1-d0) for (d0,z0),(d1,z1) in zip(zs[:-1],zs[1:])],default=0.)
        check(grade<=.14,'access_ramp_grade',[w['name'],grade])
    walk_checks.append({'name':w['name'],'samples':len(zs),'holes':len(holes),'maximum_soil_penetration_m':penetration,'stairs':w['stairs'],'riser_height_m':w['riser_height_m'],'tread_run_m':w['tread_run_m']})
cbd=[r for r in p['real_buildings'] if r.get('zone')=='CBD'];oldcbd=[r for r in old['real_buildings'] if r['instance_name'].startswith('CBD_')]
oldhull=unary_union([Polygon(r['footprint_xy']) for r in oldcbd]).convex_hull;newhull=unary_union([Polygon(r['footprint_xy']) for r in cbd]).convex_hull
check(len(cbd)==31 and all(realmap[n]['zone']=='CBD' for n in ['APT_V14_A32','APT_V14_A35']),'offices_reclassified_CBD')
govmoves=[r for r in report['moved_buildings'] if r['name'].startswith(('GOV_','MAIN_CIVIC'))];check(all(r['shore_distance_after']>190 for r in govmoves),'municipal_sites_inland')
summary={'status':'PASS' if not fail else 'FAIL','city_buildings':664,'source_meshes_preserved':len(source_before),'street_meshes_preserved':len(roads_before),'source_instances':height_checks,'all_buildings_ground_sampled':len(ground),'maximum_remaining_building_terrain_penetration_m':max(r['terrain_penetration_m'] for r in ground),'ground_corrections':len(report['ground_corrections']),'ground_penetration_details':ground,'access_checks':walk_checks,'cbd_buildings':len(cbd),'cbd_footprint_hull_before_m2':oldhull.area,'cbd_footprint_hull_after_m2':newhull.area,'municipal_shore_distance_before_mean_m':float(np.mean([r['shore_distance_before'] for r in govmoves])),'municipal_shore_distance_after_mean_m':float(np.mean([r['shore_distance_after'] for r in govmoves])),'failures':fail,'limits':'Static model and access geometry. Game collision, navigation, traffic and runtime performance are not validated.'}
(ROOT/'validation').mkdir(exist_ok=True);(ROOT/'validation/native_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print('V15_VALIDATION',summary['status'],json.dumps(fail[:20]),flush=True)
assert not fail,(len(fail),fail[:8])
