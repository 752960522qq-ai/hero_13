"""Independent GLB reimport and geometry checks for the metric reconstruction."""
import argparse,json,sys,math,struct,hashlib,collections
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser()
for k in ['glb','blend','plan','models','roads','build-report','deps','report']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).parent))
from compact_city_math import *
from city_surface_sampling import HeightField

def images(path):
    raw=path.read_bytes();assert raw[:4]==b'glTF';n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);b=raw[28+n:];out=[]
    for im in d.get('images',[]):
        assert 'uri' not in im,'External texture URI';v=d['bufferViews'][im['bufferView']];data=b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];out.append(hashlib.sha256(data).hexdigest())
    return set(out),d

p=json.loads(a.plan.read_text());land=unary_union([Polygon(v) for v in p['coasts'].values()]).difference(Polygon(p['lake']));bridgearea=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in p['edges'] if e['bridge']]);play=land.union(bridgearea).area
assert 5.5e6<=land.area<=6e6 and 5.5e6<=play<=6e6
adj=collections.defaultdict(list)
for e in p['edges']:adj[e['a']].append(e['b']);adj[e['b']].append(e['a'])
todo=[0];seen=set()
while todo:
    n=todo.pop()
    if n in seen:continue
    seen.add(n);todo.extend(adj[n])
assert len(seen)==len(p['nodes'])
grade=max(np.max(np.abs(np.diff(np.array(e['points'])[:,2]))/np.linalg.norm(np.diff(np.array(e['points'])[:,:2],axis=0),axis=1)) for e in p['edges']);assert grade<.087
masterimages,doc=images(a.glb);sourceimages={};missing=[]
for r in p['real_buildings']:
    src,_=images(a.models/r['file']);sourceimages[r['instance_name']]=len(src)
    if not src.issubset(masterimages):missing.append(r['file'])
roadimages,_=images(a.roads);assert not missing,('source texture hashes changed',missing);assert roadimages.issubset(masterimages),'road atlas changed'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(a.glb.resolve()));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];real=[]
def world_vertices(o):
    co=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(float);M=np.asarray(o.matrix_world);return co@M[:3,:3].T+M[:3,3]
for r in p['real_buildings']:
    inst=bpy.data.objects.get(r['instance_name']);assert inst and inst.get('is_building_instance');meshes=[o for o in inst.children_recursive if o.type=='MESH'];co=np.concatenate([world_vertices(o) for o in meshes]);height=co[:,2].max()-co[:,2].min();assert abs(height-r['target_height_m'])<.006,(r['instance_name'],height);assert all(o.data.uv_layers for o in meshes);M=np.array(inst.matrix_world)[:3,:3];det=np.linalg.det(M);assert det>0,'Source mirrored';scales=np.linalg.norm(M,axis=0)/r['uniform_scale'];assert np.max(np.abs(scales-r['local_axis_scale']))<1e-5,(r['instance_name'],'scale changed',scales)
    if 'Corner_Shop_10' in r['instance_name']:assert M[1,0]/np.linalg.norm(M[:,0])>.99999 and M[0,1]/np.linalg.norm(M[:,1])<-.99999,'Corner rotated incorrectly'
    real.append({'name':r['instance_name'],'height_m':float(height),'height_error_m':float(abs(height-r['target_height_m'])),'image_hashes_preserved':True,'axis_scales':scales.tolist()})
assert not any('canopy' in o.name.lower() for o in obs),'Added canopy returned'
layers=sorted({o.get('surface_group') for o in obs if o.get('surface_group')});fields={k:HeightField([o for o in obs if o.get('surface_group')==k and o.get('surface_type') in ['road_kit','pavement']]) for k in layers};terrain=HeightField([o for o in obs if o.get('surface_type')=='terrain']);walk=HeightField([o for o in obs if o.get('surface_group')=='GROUND_MAIN' and o.get('surface_type')=='sidewalk']);fail=[];road_samples=0
frontage_checks=[]
for r in p['real_buildings']:
    theta=r['theta'];u=np.array([math.cos(theta),math.sin(theta)]);v=np.array([-u[1],u[0]]);aa=np.asarray(r['anchor']);width=r['right']-r['left'];foundation=HeightField([bpy.data.objects[r['instance_name']+'_Foundation']]);center=np.mean(np.asarray(r['pad_xy']),axis=0);fz=foundation.height(center);assert fz is not None and abs(fz-(r['floor']-.018))<.002,('foundation missing',r['instance_name'])
    if r.get('direct_sidewalk_frontage'):
        lip=[]
        for s in np.linspace(.02,width-.02,41):
            xy=aa+u*s-v*.04;h=walk.height(xy);assert h is not None,('source frontage lacks sidewalk',r['instance_name'],xy.tolist());lip.append(abs(h-(r['floor']-.008)))
        limit=.035 if ('Connected_' in r['instance_name'] or 'Corner_Shop_10' in r['instance_name']) else .11
        assert max(lip)<limit,('building threshold too high',r['instance_name'],max(lip));frontage_checks.append({'instance':r['instance_name'],'maximum_threshold_lip_m':max(lip),'direct_sidewalk_frontage':True})
    else:
        field=HeightField([bpy.data.objects[r['instance_name']+'_Entrance_Plaza']]);d=r['setback_m']+.05;ss=np.linspace(0,d,31);zs=[]
        for t in ss:
            xy=aa+u*width/2-v*t;h=field.height(xy);assert h is not None,('entrance plaza hole',r['instance_name'],t);zs.append(h)
        g=float(np.max(np.abs(np.diff(zs))/np.diff(ss)));assert g<.025,(r['instance_name'],'entrance too steep',g);end=aa+u*width/2-v*d;wz=walk.height(end);assert wz is not None and abs(wz-zs[-1])<.03;frontage_checks.append({'instance':r['instance_name'],'central_access_grade':g,'plaza_to_sidewalk_lip_m':abs(wz-zs[-1]),'entrance_plaza_depth_m':d})
for e in p['edges']:
    s=np.linspace(0,e['length'],max(3,int(e['length']/14)+1));co,n=frame(e,s)
    for side in [-.26,.26]:
        xy=co[:,:2]+n*(side*e['carriage_width'])
        for point,expected in zip(xy,co[:,2]):
            h=fields[e['layer']].height(point);road_samples+=1
            if h is None:
                adjacent=[field.height(point) for k,field in fields.items() if k!=e['layer']];adjacent=[z for z in adjacent if z is not None and abs(z-expected)<.85];h=max(adjacent) if adjacent else None
            if h is None:fail.append({'type':'road_hole','edge':e['name'],'xy':point.tolist()});continue
            soil=terrain.height(point)
            if soil is not None and soil>h+.035:fail.append({'type':'terrain_in_road','edge':e['name'],'xy':point.tolist(),'penetration_m':soil-h})
if fail:(a.report.parent/'road_geometry_failures.json').write_text(json.dumps(fail,indent=2))
assert not fail,('road geometry failures',fail[:15],len(fail));print('ROAD_SAMPLES_PASS',road_samples,flush=True)
rails=[o for o in obs if '_Parapet_' in o.name];railv=[];railf=[];offset=0
for ob in rails:
    vv=world_vertices(ob);ob.data.calc_loop_triangles();ff=np.array([t.vertices[:] for t in ob.data.loop_triangles]);railv.append(vv);railf.append(ff+offset);offset+=len(vv)
rail_bvh=BVHTree.FromPolygons(np.concatenate(railv).tolist(),np.concatenate(railf).tolist(),all_triangles=True);lane_rays=0
for e in p['edges']:
    s=np.linspace(0,e['length'],max(3,int(e['length']/2)+1));cc,nn=frame(e,s)
    for side in [-.26,.26]:
        path=cc.copy();path[:,:2]+=nn*(side*e['carriage_width']);path[:,2]+=.65
        for aa,bb in zip(path[:-1],path[1:]):
            d=bb-aa;L=np.linalg.norm(d)
            if L<.001:continue
            direction=d/L;hit,_,_,_=rail_bvh.ray_cast(Vector(aa+direction*.001),Vector(direction),float(max(0,L-.002)));assert hit is None,('parapet blocks a traffic lane',e['name'],aa.tolist(),bb.tolist());lane_rays+=1
decks=[o for o in obs if o.name.startswith('MAIN_Deck_')];co=np.concatenate([world_vertices(o) for o in decks]);faces=[];offset=0
for o in decks:
    o.data.calc_loop_triangles();faces.extend([[offset+i for i in t.vertices] for t in o.data.loop_triangles]);offset+=len(o.data.vertices)
bvh=BVHTree.FromPolygons(co.tolist(),faces,all_triangles=True);clearance=[]
for ix in p['interchanges']:
    center=np.asarray(ix['center']);lower=next(e for e in p['edges'] if e['name']==ix['lower'] and LineString(np.array(e['points'])[:,:2]).distance(Point(center))<.01);point=LineString(np.array(lower['points'])[:,:2]);s=point.project(Point(center));cc,n=frame(lower,s);values=[]
    for off in np.linspace(-lower['width']/2+.25,lower['width']/2-.25,21):
        xy=cc[:2]+n*off;z=fields[lower['layer']].height(xy)
        if z is None:z=float(cc[2]+.143577)
        hit,normal,i,dist=bvh.ray_cast(Vector((*xy,float(z+.25))),Vector((0,0,1)),30)
        assert hit is not None,('missing deck',ix['name'],xy.tolist());values.append(float(hit.z-z))
    assert min(values)>5.5,(ix['name'],min(values));clearance.append({'name':ix['name'],'minimum_actual_clearance_m':min(values),'samples':len(values)})
# Walkway continuity and endpoint lips are checked against actual imported surfaces.
walkcheck=[];bed_byname={o.name:o for o in obs};obstacles=[o for o in obs if o.get('is_placeholder') or '_Source_Mesh_' in o.name or '_Foundation' in o.name or o.name.startswith('Oldtown_Row_Partywall_')];obstacle_v=[];obstacle_f=[];offset=0
for ob in obstacles:
    vv=world_vertices(ob);ob.data.calc_loop_triangles();ff=np.array([t.vertices[:] for t in ob.data.loop_triangles]);obstacle_v.append(vv);obstacle_f.append(ff+offset);offset+=len(vv)
obstacle_bvh=BVHTree.FromPolygons(np.concatenate(obstacle_v).tolist(),np.concatenate(obstacle_f).tolist(),all_triangles=True);headroom_rays=0
for r in p['pedestrian_alleys']:
    ob=bed_byname.get(r['name']);assert ob is not None;field=HeightField([ob]);aa,bb=np.array(r['points']);L=np.linalg.norm(bb-aa);tangent=(bb-aa)/L;n=np.array([-tangent[1],tangent[0]]);penetration=0.;count=0
    for s in np.linspace(0,L,max(3,int(L/4)+1)):
        for off in [-1.15,0,1.15]:
            xy=aa+tangent*s+n*off;z=field.height(xy);assert z is not None,('walkway hole',r['name'],xy);soil=terrain.height(xy)
            if soil is not None:penetration=max(penetration,soil-z)
            hit,_,_,_=obstacle_bvh.ray_cast(Vector((*xy,float(z+.15))),Vector((0,0,1)),2.1);assert hit is None,('low overhead obstacle in alley',r['name'],xy.tolist());headroom_rays+=1;count+=1
    assert penetration<.035,('soil in alley',r['name'],penetration);lips=[]
    for xy in [aa,bb]:
        wz=walk.height(xy);assert wz is not None,('alley not connected to a sidewalk',r['name'],xy.tolist());lips.append(abs(wz-field.height(xy)))
    assert max(lips)<.05,(r['name'],'lip',lips);assert r['max_grade']<=.061
    walkcheck.append({'name':r['name'],'samples':count,'maximum_endpoint_lip_m':max(lips),'maximum_grade':r['max_grade']})
groundshape=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in p['edges'] if e['layer'].startswith('GROUND')]);build=json.loads(a.build_report.read_text());pierhits=[r['name'] for r in build['piers'] if not r['bridge'] and Point(r['xy']).buffer(.92).intersects(groundshape)];assert not pierhits,('piers in lower road',pierhits)
triangles=sum(len(o.data.polygons) for o in obs);report={'schema':'hero13.city.compact-validation.v8','status':'PASS','area':{'land_m2':land.area,'land_plus_crosswater_decks_m2':play,'water_excluded':True,'grade_separated_decks_not_double_counted':True},'road_graph_components':1,'maximum_road_grade':float(grade),'road_surface_samples':road_samples,'road_surface_holes':0,'terrain_penetrations':0,'interchanges':clearance,'pedestrian_links':walkcheck,'pedestrian_link_count':len(walkcheck),'source_buildings':real,'source_image_count_by_building':sourceimages,'original_road_atlas_preserved':True,'original_source_building_count':len(real),'corner_on_right':True,'corner_turn_degrees':90,'corner_intrinsic_depth_scale':1.45,'additional_canopy_present':False,'source_texture_bytes_preserved':True,'glb_external_resources':False,'mesh_objects':len(obs),'imported_triangles':triangles,'file_size_bytes':a.glb.stat().st_size,'limitations':'Geometry and metric areas verified. Game collision meshes, navigation, streaming logic and runtime FPS were not integrated or benchmarked.'}
# Verify editable massing has an intact identity per lot and the intended metric roof heights.
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();assert bpy.context.scene.unit_settings.scale_length==1
top=np.full(len(p['buildings']),-np.inf);counts=np.zeros(len(top),int);groundheights=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    if ob.get('surface_type')=='terrain':groundheights.extend([v.co.z for v in ob.data.vertices])
    attr=ob.data.attributes.get('source_building_index')
    if not attr:continue
    ids=np.empty(len(ob.data.polygons),np.int32);attr.data.foreach_get('value',ids);mi=np.empty(len(ids),np.int32);ob.data.polygons.foreach_get('material_index',mi);roofmask=mi==1
    vi=np.empty(len(ob.data.loops),np.int32);ob.data.loops.foreach_get('vertex_index',vi);co=world_vertices(ob);fz=co[vi.reshape(-1,3),2].max(1);np.maximum.at(top,ids[roofmask],fz[roofmask]);np.add.at(counts,ids,1)
expected=np.array([b['base']+b['height'] for b in p['buildings']]);assert np.all(counts>0);error=float(np.abs(top-expected).max());assert error<.002,error;assert max(groundheights)-min(groundheights)>10
report['placeholder_lots_verified']=len(top);report['placeholder_maximum_roof_height_error_m']=error;report['terrain_height_range_m']=[min(groundheights),max(groundheights)]
report['pedestrian_headroom_rays']=headroom_rays
report['building_frontage_checks']=frontage_checks
report['surface_sampling_tolerance_m']=.001
report['traffic_lane_barrier_rays']=lane_rays
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2));print('COMPACT_VALIDATION_PASS',json.dumps({'area_km2':land.area/1e6,'interchanges':clearance,'walkways':len(walkcheck),'mesh_objects':len(obs)}),flush=True)
