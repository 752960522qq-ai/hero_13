"""Concentrate CBD/civic sites and correct terrain penetration in city world space.

Run with Blender 4.5 against a recovered v14 native model. Source mesh data,
textures and scales remain unchanged; the script transforms instance roots.
"""
import bpy,sys,json,copy,math,hashlib,csv
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/workspace/scratch/705f52588668/work_v14/model')
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.ops import substring
from city_surface_sampling import HeightField
MODEL=ROOT/'model';MODEL.mkdir(exist_ok=True)
p=json.loads((BASE/'city_plan.json').read_text());old=copy.deepcopy(p);layout=json.loads((ROOT/'layout.json').read_text());sites={s['name']:s for s in layout['sites']}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));sc=bpy.context.scene;bpy.context.view_layer.update()
footparent=bpy.data.objects['08_BUILDING_FOOTINGS'];walkparent=bpy.data.objects['10_PEDESTRIAN_NETWORK']
def fingerprint(o):
    h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());m=o.data
    for ar in [np.array([v.co[:] for v in m.vertices],dtype='<f4'),np.array([len(q.vertices) for q in m.polygons],dtype='<i4'),np.array([v for q in m.polygons for v in q.vertices],dtype='<i4'),np.array([q.material_index for q in m.polygons],dtype='<i4')]:h.update(ar.tobytes())
    for uv in m.uv_layers:h.update(np.array([q.uv[:] for q in uv.data],dtype='<f4').tobytes())
    return h.hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
terrain_obs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'];soil=HeightField(terrain_obs)
terrain_mat=terrain_obs[0].data.materials[0];concrete=bpy.data.materials['Bridge_Concrete'];atlas=bpy.data.materials['Road_Modular_Original_Atlas']
terrain_color=np.array([v.color[:] for v in terrain_obs[0].data.color_attributes[0].data]).mean(0).tolist()
walk_names={q['name'] for q in p['pedestrian_alleys']}
def iswalk(o):return o.type=='MESH' and (o.get('surface_type') in ['sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk','v14_access_walk'] or o.name in walk_names)
roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.05,join_style=2) for e in p['edges']])
carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.1,join_style=2) for e in p['edges']])
reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
def mesh(name,verts,faces,mat,parent=footparent,terrain=False,uv=False):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=parent;o['modified_in_version']='v15'
    if terrain:
        m.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.tile(terrain_color,(len(verts),1)).astype(np.float32).ravel());o['surface_type']='terrain'
    if uv:
        layer=m.uv_layers.new(name='UVMap')
        for i,loop in enumerate(m.loops):
            q=m.vertices[loop.vertex_index].co;layer.data[i].uv=(.216+.055*((q.x/3)%1),.5989+.1777*((q.y/16.9048)%1))
    if parent==walkparent and not terrain:o['surface_type']='v15_access_walk'
    return o
def prism(poly,top,bottom,name):
    xy=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:-1];n=len(xy);v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];f=[]
    for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
    for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
    return mesh(name,v.tolist(),f,concrete)
def surface(poly,height,name,mat=atlas,parent=walkparent,ground=False,step=1.8):
    vv=[];ff=[]
    for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(poly,step))):
        xy=np.array(tri.exterior.coords)[:3]
        if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
        k=len(vv);vv.extend([[*q,height(q)] for q in xy]);ff.append([k,k+1,k+2])
    if not ff:return None
    return mesh(name,vv,ff,mat,parent,ground,not ground)
def nearest_soil(q):
    z=soil.height(q)
    if z is not None:return z
    hit,_,idx,_=soil.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)))
    tri=soil.tri[idx];A=np.vstack([tri[:,:2].T,np.ones(3)]);weights=np.linalg.solve(A,np.r_[np.array(hit[:2]),1.]);return float(weights@tri[:,2])
def object_xy(o):
    o.data.calc_loop_triangles();co=np.array([v.co[:] for v in o.data.vertices]);M=np.array(o.matrix_world);co=co@M[:3,:3].T+M[:3,3];polys=[]
    for tr in o.data.loop_triangles:
        q=Polygon(co[list(tr.vertices),:2])
        if q.area>1e-8:polys.append(q)
    return unary_union(polys)
def filter_faces(ob,keep):
    m=ob.data
    if all(keep):return
    if not any(keep):bpy.data.objects.remove(ob,do_unlink=True);return
    new=bpy.data.meshes.new(m.name+'_v15');new.from_pydata([v.co[:] for v in m.vertices],[],[list(f.vertices) for f,k in zip(m.polygons,keep) if k])
    for mat in m.materials:new.materials.append(mat)
    new.polygons.foreach_set('material_index',np.array([f.material_index for f,k in zip(m.polygons,keep) if k],np.int32));new.update();ob.data=new
# Keep the native model's instance meshes, removing only their obsolete footings
# and access surfaces. Their projected holes are restored below.
moving_sources={r['instance_name'] for r in p['real_buildings'] if r['instance_name'] in sites}
moving_objects=set()
for n in moving_sources:moving_objects.update(o.name for o in bpy.data.objects[n].children_recursive if o.type=='MESH')
restore_shapes=[];removed_objects=[]
for r in old['real_buildings']:
    if r['instance_name'] in sites:restore_shapes.append(Polygon(r['pad_xy']).buffer(.15))
for o in list(sc.objects):
    if o.type!='MESH' or o.name in moving_objects:continue
    if any(o.name.startswith(n+'_') for n in moving_sources):
        if o.get('surface_type') or 'Entrance' in o.name:restore_shapes.append(object_xy(o).buffer(.03))
        removed_objects.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
restore=unary_union(restore_shapes).difference(roads.buffer(.01)).difference(reserve.buffer(.01))
restore_buffer=restore.buffer(.5)
# Remove only old retaining segments for the vacated sites, keeping other cuts.
for o in list(sc.objects):
    if o.type!='MESH' or o.get('surface_type')!='terrain_cut_retaining_wall':continue
    co=np.array([v.co[:] for v in o.data.vertices]);keep=[]
    for f in o.data.polygons:keep.append(not restore_buffer.covers(Point(co[list(f.vertices),:2].mean(0))))
    filter_faces(o,keep)
# Only fill actual terrain holes. Existing ground, streets and retained sites
# continue to use their original vertices and materials.
ground_polys=[Polygon(tr[:,:2]) for tr in soil.tri];tree=shapely.STRtree(ground_polys);near=tree.query(restore)
covered=unary_union([ground_polys[i] for i in near]);holes=restore.difference(covered)
restored_area=0.
for i,part in enumerate(shapely.get_parts(holes)):
    if part.geom_type!='Polygon' or part.area<.001:continue
    surface(part,nearest_soil,f'V15_Vacated_Ground_{i:03d}',terrain_mat,bpy.data.objects['01_TERRAIN'],True,2.)
    restored_area+=part.area
print('RESTORED_OLD_SITES',round(restored_area,2),flush=True)
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
oldwalk=HeightField([o for o in sc.objects if iswalk(o)])
allwalk=[o for o in sc.objects if iswalk(o)]
realmap={r['instance_name']:r for r in p['real_buildings']};boxmap={b['name']:b for b in p['buildings']};newcuts=[];walks=[];moves=[]
# Keep a proper civic forecourt in front of the main building. Support volumes
# form three short rows around it rather than crowding its facade.
govnames=[n for n,s in sites.items() if s['kind']=='gov' and n!='GOV_V14_G33']
govcenters=[[390,770],[390,823],[390,876],[438,770],[438,882],[490,766],[545,770],[558,823],[558,882]]
for name,center in [('GOV_V14_G33',[500,870]),*zip(govnames,govcenters)]:
    s=sites[name];r=realmap.get(name,boxmap.get(name));oldpoly=Polygon(r.get('footprint_xy',r.get('footprint')));xy=np.array(oldpoly.exterior.coords)[:-1]-np.array(r['center']);delta=180 if name=='GOV_V14_G33' else 0
    R=np.array([[math.cos(math.radians(delta)),-math.sin(math.radians(delta))],[math.sin(math.radians(delta)),math.cos(math.radians(delta))]])
    s['center']=center;s['rotation_delta_degrees']=delta;s['footprint']=(xy@R.T+np.array(center)).tolist()
all_site_polys={n:Polygon(s['footprint']) for n,s in sites.items()}
access_goals=[]
for e in p['edges']:
    if e['region']!='MAIN':continue
    line=LineString(np.array(e['points'])[:,:2])
    for side in ['left','right']:
        off=line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.65,side,join_style=2)
        for part in shapely.get_parts(off):
            if part.geom_type=='LineString':access_goals.append((e['name']+'_'+side,part))
used_corridors=[]
def choose_access(name,poly,floor):
    obstacles=unary_union([q.buffer(.25,join_style=2) for n,q in all_site_polys.items() if n!=name]+[Polygon(b['footprint']) for b in p['buildings'] if b['name'] not in sites]+[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r['instance_name'] not in sites]+[reserve])
    coords=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:4];options=[];pad=poly.buffer(2.3,join_style=2)
    bad=unary_union([carriage,obstacles,poly.buffer(-.01)]);shapely.prepare(bad)
    nearest=sorted(access_goals,key=lambda g:g[1].distance(poly))[:18]
    for aa,bb in zip(coords,np.roll(coords,-1,axis=0)):
        mid=(aa+bb)/2;u=(bb-aa)/np.linalg.norm(bb-aa);normal=np.array([u[1],-u[0]]);start=mid+normal*2.28
        if obstacles.intersects(Point(start).buffer(1.6)):continue
        for gn,gl in nearest:
            at=gl.project(Point(start))
            for off in [0,-18,18,-40,40,-70,70]:
                end=np.array(gl.interpolate(np.clip(at+off,0,gl.length)).coords[0]);gz=oldwalk.height(end)
                if gz is None:continue
                lead=start+normal*2.6
                variants=[[start,end],[start,[start[0],end[1]],end],[start,[end[0],start[1]],end], [start,lead,[end[0],lead[1]],end], [start,lead,[lead[0],end[1]],end]]
                for vv in variants:
                    vv=np.array(vv,float);vv=vv[np.r_[True,np.linalg.norm(np.diff(vv,axis=0),axis=1)>.02]]
                    if len(vv)<2:continue
                    direction=vv[1]-vv[0]
                    if direction@normal/np.linalg.norm(direction)<.70:continue
                    route=LineString(vv);L=route.length
                    if L<3 or L>200:continue
                    strip=route.buffer(1.6,cap_style=2,join_style=2)
                    if bad.intersects(strip):continue
                    inter=route.intersection(pad);exitd=max([route.project(Point(q)) for part in shapely.get_parts(inter) if part.geom_type=='LineString' for q in part.coords],default=0.)
                    endd=L
                    for dd in np.arange(.08,min(7.,L-exitd-.3),.08):
                        q=route.interpolate(L-dd).coords[0]
                        if oldwalk.height(q) is None:break
                        endd=L-dd
                    if endd-exitd<.5:continue
                    endh=oldwalk.height(route.interpolate(endd).coords[0]);endh=gz if endh is None else endh
                    grade=abs(floor-.025-endh)/max(.2,endd-exitd)
                    if grade>.48:continue
                    score=L*.12+max(0,grade-.10)*65+abs(floor-.025-gz)*.3
                    options.append((score,route,gn,float(gz)))
    if not options:raise RuntimeError(('No usable entrance',name))
    _,route,gn,gz=min(options,key=lambda v:v[0]);return route,gn,gz
def lot_vertices(index):
    for ob in sc.objects:
        if ob.type!='MESH':continue
        attr=ob.data.attributes.get('source_building_index')
        if not attr:continue
        ids=np.array([v.value for v in attr.data]);faces=np.flatnonzero(ids==index)
        if not len(faces):continue
        used=sorted({vi for fi in faces for vi in ob.data.polygons[int(fi)].vertices});yield ob,used
def soil_samples(poly):
    pts=list(shapely.segmentize(poly.exterior,1.5).coords);xmin,ymin,xmax,ymax=poly.bounds
    for x in np.arange(xmin,xmax,3.):
        for y in np.arange(ymin,ymax,3.):
            if poly.covers(Point(x,y)):pts.append((x,y))
    return [nearest_soil(q) for q in pts]
for name,s in sites.items():
    r=realmap.get(name,boxmap.get(name));isreal=name in realmap;poly=Polygon(s['footprint']);oldcenter=np.array(r['center'],float);oldfloor=r.get('floor',r.get('base'));newcenter=np.array(s['center'],float);angle=math.radians(s['rotation_delta_degrees'])
    pad=poly.buffer(2.3,join_style=2);floor=max(soil_samples(pad))+.075
    route,goal_name,gz=choose_access(name,poly,floor);s['route']=[list(q) for q in route.coords];s['goal_name']=goal_name;goal=np.array(s['route'][-1])
    assert gz is not None,('No existing sidewalk at goal',name,goal)
    # Lower the surroundings on the entrance side only; never move the road.
    plateau=floor-.025;L=route.length;inter=route.intersection(pad);startland=max([route.project(Point(q)) for part in shapely.get_parts(inter) if part.geom_type=='LineString' for q in part.coords],default=0.);endland=L
    for dd in np.arange(.08,min(7.,L-startland-.3),.08):
        if oldwalk.height(route.interpolate(L-dd).coords[0]) is None:break
        endland=L-dd
    joinxy=np.array(route.interpolate(endland).coords[0]);joinh=oldwalk.height(joinxy);joinh=gz if joinh is None else joinh;run=max(.2,endland-startland);grade=abs(plateau-joinh)/run
    grad=[]
    for axis in range(2):
        delta=np.zeros(2);delta[axis]=.1;z0=oldwalk.height(joinxy-delta);z1=oldwalk.height(joinxy+delta);grad.append((z1-z0)/.2 if z0 is not None and z1 is not None else 0.)
    grad=np.array(grad)
    support_bottom=min([floor-.5,*soil_samples(pad)])-.2
    T=Matrix.Translation((*newcenter,floor))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation((-oldcenter[0],-oldcenter[1],-oldfloor))
    if isreal:
        inst=bpy.data.objects[name];inst.matrix_world=T@inst.matrix_world
        if name in ['CBD_Office_Building_01','CBD_Modern_Glass_02']:
            bpy.context.view_layer.update();low=min((o.matrix_world@v.co).z for o in inst.children_recursive if o.type=='MESH' for v in o.data.vertices);inst.location.z+=(floor-.008)-low
        for key in ['anchor','access_start_xy','access_end_xy']:
            if key in r:
                v=T@Vector((*r[key],oldfloor));r[key]=list(v[:2])
        r.update(center=list(newcenter),footprint_xy=s['footprint'],pad_xy=list(pad.exterior.coords),floor=floor,foundation_bottom_m=support_bottom,theta=r['theta']+angle,angle=math.degrees(r['theta']+angle),modified_in_version='v15',zone='CBD' if s['kind']=='cbd' else 'GOVERNMENT')
        if name in layout['office_reclassified']:r.update(typology='office_source_building',use_corrected_in='v15',previous_zone='APARTMENT')
        inst['zone']=r['zone'];inst['modified_in_version']='v15'
    else:
        index=p['buildings'].index(r)
        for ob,indices in lot_vertices(index):
            inv=ob.matrix_world.inverted()
            for vi in indices:ob.data.vertices[vi].co=inv@T@ob.matrix_world@ob.data.vertices[vi].co
            ob.data.update()
        r.update(center=list(newcenter),footprint=s['footprint'],base=floor,zone='GOVERNMENT',planning_area='INLAND_MUNICIPAL_CAMPUS',modified_in_version='v15')
    prism(pad,plateau,support_bottom,name+'_Foundation');r['access_alley']=name+'_Entrance_Walk_V15'
    # A ground-level apron around every facade removes the tall terrain lip.
    ob=surface(pad.difference(poly.buffer(.04)),lambda q:plateau,name+'_Site_Apron_V15');ob['surface_type']='v15_site_apron';ob['site_building']=name
    corridor=route.buffer(1.6,cap_style=2,join_style=2).union(pad).difference(poly.buffer(.035));outside=corridor.difference(pad)
    steps=max(1,int(math.ceil(abs(plateau-joinh)/.15))) if grade>.10 else 0
    def walkway_height(q):
        q=np.array(q)
        if pad.buffer(.00001).covers(Point(q)):return plateau
        existing=oldwalk.height(q)
        if existing is not None:return existing+.001
        d=route.project(Point(q));t=float(np.clip((d-startland)/run,0.,1.))
        if steps:t=math.floor(t*steps+1e-6)/steps
        plane=joinh+.001+float(grad@(q-joinxy))
        return plateau*(1-t)+plane*t
    # Split at stair risers. Separate vertical quads close each tread edge.
    if steps:
        a0=np.array(s['route'][0]);vec=(goal-np.array(s['route'][-2]));vec/=np.linalg.norm(vec);last=plateau
        for j in range(steps):
            d0=startland+run*j/steps;d1=startland+run*(j+1)/steps
            seg=substring(route,d0,d1).buffer(1.6,cap_style=2,join_style=2).difference(pad).difference(poly.buffer(.035));z=plateau+(joinh-plateau)*j/steps
            if not seg.is_empty:surface(seg,lambda q,z=z:z,name+f'_Stair_Tread_{j:02d}')
            xy=np.array(route.interpolate(d1).coords[0]);v0=np.array(route.interpolate(max(0,d1-.02)).coords[0]);v1=np.array(route.interpolate(min(L,d1+.02)).coords[0]);tangent=(v1-v0)/max(1e-8,np.linalg.norm(v1-v0));n=np.array([-tangent[1],tangent[0]]);zn=plateau+(joinh-plateau)*(j+1)/steps;aa=xy-n*1.6;bb=xy+n*1.6
            mesh(name+f'_Stair_Riser_{j:02d}',[[*aa,z],[*bb,z],[*bb,zn],[*aa,zn]],[[0,1,2],[0,2,3]],concrete)
        startpart=substring(route,0,max(.001,startland)).buffer(1.6,cap_style=2,join_style=2).difference(pad)
        if not startpart.is_empty:surface(startpart,lambda q:plateau,name+'_Entrance_Landing_V15')
        # Join the last tread exactly to the existing sidewalk.
        lastpart=substring(route,max(0,endland-.03),L).buffer(1.6,cap_style=2,join_style=2).difference(carriage)
        surface(lastpart,lambda q:(oldwalk.height(q) if oldwalk.height(q) is not None else joinh+float(grad@(np.array(q)-joinxy)))+.001,name+'_Sidewalk_Join_V15')
    elif not outside.is_empty:
        surface(outside,walkway_height,r['access_alley'])
    cuts=unary_union([pad,corridor.buffer(.015)]).difference(roads.buffer(-.75));newcuts.append(cuts)
    walks.append({'name':r['access_alley'],'building':name,'polygon':list(corridor.exterior.coords),'route':s['route'],'goal':goal.tolist(),'goal_z':gz,'floor_surface':plateau,'goal_name':s['goal_name'],'maximum_grade_if_ramp':grade,'ramp_start':startland,'ramp_end':endland,'stairs':bool(steps),'riser_count':steps,'riser_height_m':abs(plateau-joinh)/steps if steps else 0.,'tread_run_m':run/steps if steps else 0.})
    moves.append({'name':name,'old_center':list(oldcenter),'new_center':list(newcenter),'old_floor':oldfloor,'new_floor':floor,'foundation_top':plateau,'source_mesh_unchanged':isreal,'shore_distance_before':Polygon(p['coasts']['MAIN']).boundary.distance(Point(oldcenter)),'shore_distance_after':Polygon(p['coasts']['MAIN']).boundary.distance(Point(newcenter))})
    print('MOVED',name,[round(v,2) for v in newcenter],'floor',round(floor,2),'grade',round(grade,3),'stairs',steps,flush=True)
# Independently raise the bottoms of all actually penetrated placeholder lots.
# Only their labelled vertices move. Other lots sharing a mesh remain identical.
audit=json.loads((ROOT/'ground_audit_before.json').read_text());lifts=[]
for n,depth in {'MAIN_OLDTOWN_0178':.08480451288233937,'EAST_INDUSTRIAL_0013':.12841295660918206}.items():
    next(q for q in audit if q['name']==n)['inside_max']=depth
for q in audit:
    name=q['name']
    if name in sites or name not in boxmap or (q['inside_max'] or 0)<=.08:continue
    r=boxmap[name];poly=Polygon(r['footprint']);base=r['base'];newbase=max([base,*soil_samples(poly.buffer(.35,join_style=2))])+.065;dz=newbase-base;idx=p['buildings'].index(r)
    for ob,indices in lot_vertices(idx):
        for vi in indices:ob.data.vertices[vi].co.z+=dz
        ob.data.update()
    # Dedicated existing decorations/footings follow the lot's new elevation.
    for ob in list(sc.objects):
        if ob.type=='MESH' and ob.name.startswith(name+'_') and not ob.data.attributes.get('source_building_index'):ob.location.z+=dz
    prism(poly.buffer(.09,join_style=2),newbase-.022,base-3.6,name+'_Ground_Correction_Foundation_V15')
    r['base']=newbase;r['ground_corrected_in']='v15';lifts.append({'name':name,'old_base':base,'new_base':newbase,'lift_m':dz,'prior_terrain_penetration_m':q['inside_max']})
print('GROUND_CORRECTIONS',len(lifts),flush=True)
# Cut the terrain exactly beneath the new pads and stairs. Interpolate retained
# triangles so their boundary vertices remain aligned with adjacent districts.
cuts=unary_union(newcuts);cut_faces=0
for ob in [o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']:
    m=ob.data;m.calc_loop_triangles();co=np.array([v.co[:] for v in m.vertices]);local=cuts.intersection(box(co[:,0].min(),co[:,1].min(),co[:,0].max(),co[:,1].max()))
    if local.is_empty:continue
    vv=[];ff=[];cc=[];mats=[];changes=0;oldc=np.array([v.color[:] for v in m.color_attributes[0].data]) if m.color_attributes else None
    for tr in m.loop_triangles:
        ids=list(tr.vertices);xyz=co[ids];q=Polygon(xyz[:,:2]);parts=[xyz]
        if q.area<1e-10:continue
        if q.intersects(local):
            diff=q.difference(local)
            if q.area-diff.area>1e-8:
                changes+=1;parts=[]
                if not diff.is_empty:
                    for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
                        xy=np.array(tri.exterior.coords)[:3];A=np.vstack([xyz[:,:2].T,np.ones(3)]);w=np.linalg.solve(A,np.vstack([xy.T,np.ones(3)]));parts.append(np.c_[xy,w.T@xyz[:,2]])
        for part in parts:
            if np.cross(part[1,:2]-part[0,:2],part[2,:2]-part[0,:2])<0:part=part[::-1]
            k=len(vv);vv.extend(part.tolist());ff.append([k,k+1,k+2]);mats.append(m.polygons[tr.polygon_index].material_index)
            if oldc is not None:
                weights=np.linalg.solve(np.vstack([xyz[:,:2].T,np.ones(3)]),np.vstack([part[:,:2].T,np.ones(3)]));cc.extend((weights.T@oldc[ids]).tolist())
    if not changes:continue
    new=bpy.data.meshes.new(m.name+'_v15');new.from_pydata(vv,[],ff)
    for mat in m.materials:new.materials.append(mat)
    new.polygons.foreach_set('material_index',np.array(mats,np.int32))
    if cc:new.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(cc,np.float32).ravel())
    new.update();ob.data=new;cut_faces+=changes
# Retain the outer soil beside each new raised site, never raising it against
# the source facade. The entrance apron is the flat datum for the whole site.
soil_final=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);vv=[];ff=[]
for name,s in sites.items():
    r=realmap.get(name,boxmap.get(name));pad=Polygon(r.get('pad_xy',Polygon(s['footprint']).buffer(2.3,join_style=2).exterior.coords));top=r.get('floor',r.get('base'))-.025
    ring=np.array(shapely.segmentize(pad.exterior,2.).coords)
    for aa,bb in zip(ring[:-1],ring[1:]):
        zs=[nearest_soil(q) for q in [aa,bb]];k=len(vv);vv.extend([[*aa,zs[0]-.12],[*bb,zs[1]-.12],[*bb,top],[*aa,top]]);ff.extend([[k,k+1,k+2],[k,k+2,k+3]])
mesh('V15_Site_Perimeter_Retaining_Walls',vv,ff,concrete)['surface_type']='terrain_cut_retaining_wall'
# Update canonical metadata, keeping IDs and counts stable.
for k in ['access_v14','cbd_access_v13','infill_access_v12']:
    p[k]=[w for w in p[k] if w.get('building',w.get('instance_name')) not in sites and not any(str(w.get('name','')).startswith(n+'_') for n in sites)]
p['access_v15']=walks;p['schema']='hero13.city.regional-update.v15'
p['cbd_plan'].update(boundary=[[-383,727],[330,727],[330,1085],[-383,1085],[-383,727]],boundary_area_m2=713*358,core_boundary=layout['cbd_core_polygon'],core_area_m2=Polygon(layout['cbd_core_polygon']).area,existing_buildings=31,source_buildings=31,planned_total_including_tianming=32,placeholder_buildings=0,version='v15',reclassified_from_apartment=layout['office_reclassified'])
govsite=unary_union([Polygon(s['footprint']) for s in sites.values() if s['kind']=='gov']).convex_hull.buffer(5,join_style=2)
p['urban_areas_v14']['municipal_campus'].update(name_zh='内陆集中市政区',polygon=list(govsite.exterior.coords),area_m2=govsite.area,support_buildings=[r['name'] for r in p['buildings'] if r['zone']=='GOVERNMENT'],government_facade_towards='existing inland streets',relocated_in='v15')
apt=p['urban_areas_v14']['north_apartments'];apt.update(source_towers=['APT_V14_A36'],building_units=10,source_tower_use='remaining apartment highrise; A32 and A35 corrected to CBD offices',updated_in='v15')
p['stats'].update(cbd_buildings=31,apartment_buildings=10,government_area_buildings=10)
from collections import Counter
counts=Counter(b['zone'] for b in p['buildings']);counts.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings']);p['stats']['building_count_by_zone']=dict(counts)
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
changed=[n for n,h in after.items() if before.get(n)!=h];deleted=sorted(set(before)-set(after));unchanged=[n for n,h in after.items() if before.get(n)==h]
report={'version':'v15','base_version':'v14','base_commit':'c8f042ef1378a2f140d479eb46e6b2c9e9db2deb','building_count':len(p['buildings'])+len(p['real_buildings']),'moved_buildings':moves,'ground_corrections':lifts,'changed_objects':changed,'removed_objects':deleted,'unchanged_object_fingerprints':{n:before[n] for n in unchanged},'restored_vacated_ground_area_m2':restored_area,'terrain_triangles_cut':cut_faces,'cbd_boundary_area_before_m2':old['cbd_plan']['boundary_area_m2'],'cbd_boundary_area_after_m2':p['cbd_plan']['boundary_area_m2'],'cbd_core_area_m2':p['cbd_plan']['core_area_m2'],'road_geometry_unchanged':True,'tianming_reservation_unchanged':True,'source_building_count':len(p['real_buildings']),'placeholder_count':len(p['buildings'])}
(MODEL/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(MODEL/'v15_build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(MODEL/'tianming_reservation.json').write_text(json.dumps(p['cbd_plan']['tianming'],ensure_ascii=False,indent=2))
with (MODEL/'building_registry.csv').open('w',newline='') as f:
    fields=['id','kind','zone','source_file','x','y','floor_m','height_m','count_units'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for b in p['buildings']+p['real_buildings']:w.writerow({'id':b.get('name',b.get('instance_name')),'kind':'source' if 'instance_name' in b else 'placeholder','zone':b.get('zone','CBD' if b.get('instance_name','').startswith('CBD_') else 'OLDTOWN'),'source_file':b.get('file',''),'x':b['center'][0],'y':b['center'][1],'floor_m':b.get('floor',b.get('base')),'height_m':b.get('target_height_m',b.get('height')),'count_units':1})
bpy.data.objects['Huizhou_Reconstructed_City_3p25km2']['version']='v15_compact_CBD_inland_civic_ground_corrections'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/'huizhou_road_network.blend'),compress=True)
print('V15_BUILD_DONE',json.dumps({'moved':len(moves),'ground_corrected':len(lifts),'changed_meshes':len(changed),'unchanged_meshes':len(unchanged)}),flush=True)
