"""Rebuild entrance paths as ordered treads/strip sections, preserving platform edges.

The long polygon triangulation can span a bend or the flat building platform.
Explicit cross sections enforce the height profile at every turn and landing.
"""
import bpy,json,sys,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import substring
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/huizhou_road_network.blend'));sc=bpy.context.scene;p=json.load(open(ROOT/'model/city_plan.json'));validation=json.load(open(ROOT/'validation/native_validation.json'))
bad={r['details'][0] for r in validation['failures'] if r['check']=='access_ramp_grade'}
policy=ROOT/'access_profile_policy.json'
if policy.exists():bad=set(json.loads(policy.read_text())['stepped_entrances'])
else:policy.write_text(json.dumps({'stepped_entrances':sorted(bad)},indent=2))
names={q['name'] for q in p['pedestrian_alleys']};oldwalk=HeightField([o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk','v14_access_walk'] or o.name in names)])
records={r.get('name',r.get('instance_name')):r for r in p['buildings']+p['real_buildings']}
for w in p['access_v15']:
    r=records[w['building']];poly=Polygon(r.get('footprint_xy',r.get('footprint')));pad=poly.buffer(2.3,join_style=2);route=LineString(w['route']);L=route.length;P=np.array(route.coords);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))];plateau=w['floor_surface'];start=w['ramp_start'];end=w['ramp_end'];endxy=np.array(route.interpolate(end).coords[0]);target=oldwalk.height(endxy)
    if target is None:target=w['goal_z']
    steps=w['riser_count']
    if w['name'] in bad:steps=max(1,int(math.ceil(abs(plateau-target)/.12)))
    windows=[(max(0.,d-1.6),min(L,d+1.6)) for d in ds[1:-1]]
    def advance(d):
        stop=float(np.clip(d,start,end));return stop-start-sum(max(0,min(stop,b)-max(start,a)) for a,b in windows)
    run=advance(end)
    if steps:
        if run/steps<.3:steps=max(1,int(run/.3))
        if abs(plateau-target)/steps>.175:raise RuntimeError(('Stair riser too high',w['name']))
        w.update(stairs=True,riser_count=steps,riser_height_m=abs(plateau-target)/steps,tread_run_m=run/steps)
    risers=[]
    if steps:
        for i in range(1,steps+1):
            lo,hi=start,end
            for _ in range(45):
                mid=(lo+hi)/2
                if advance(mid)<run*i/steps:lo=mid
                else:hi=mid
            risers.append((lo+hi)/2)
    stations=sorted(set([0.,start,end,L,*[q for ab in windows for q in ab],*np.linspace(0,L,int(L/.4)+2).tolist(),*risers]));stations=[d for i,d in enumerate(stations) if (i==0 or d-stations[i-1]>1e-6) and not any(a+1e-6<d<b-1e-6 for a,b in windows)]
    def section(d):
        q=np.array(route.interpolate(d).coords[0]);idx=np.searchsorted(ds,d,side='right')-1;idx=int(np.clip(idx,0,len(P)-2));u=(P[idx+1]-P[idx]);u/=np.linalg.norm(u);n=np.array([-u[1],u[0]])
        return q+n*1.6,q-n*1.6
    def centerz(d):
        if d<=start:return plateau
        if d>=end:
            z=oldwalk.height(route.interpolate(d).coords[0]);return target if z is None else z+.001
        t=advance(d)/run
        if steps:t=math.floor(t*steps+1e-5)/steps
        return plateau+(target-plateau)*t
    vv=[];ff=[];mi=[]
    def emit(shape,zfun,material=0):
        if shape.is_empty:return
        for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(shape)):
            xy=np.array(tri.exterior.coords)[:3]
            if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
            k=len(vv);vv.extend([[*q,zfun(q)] for q in xy]);ff.append([k,k+1,k+2]);mi.append(material)
    emit(shapely.segmentize(pad.difference(poly.buffer(.035)),1.),lambda q:plateau)
    for a,b in windows:
        landing=substring(route,a,b).buffer(1.6,cap_style=2,join_style=2).difference(pad);z=centerz((a+b)/2);emit(landing,lambda q,z=z:z)
    for d0,d1 in zip(stations[:-1],stations[1:]):
        if any(a<(d0+d1)/2<b for a,b in windows):continue
        a,b=section(d0);c,d=section(d1);shape=Polygon([a,b,d,c]).difference(pad);mid=(d0+d1)/2
        if steps and start<mid<end:
            z=centerz(mid);emit(shape,lambda q,z=z:z)
        else:
            z0=centerz(d0);z1=centerz(d1)
            def height(q):
                if pad.buffer(1e-5).covers(Point(q)):return plateau
                frac=float(np.clip((route.project(Point(q))-d0)/max(1e-8,d1-d0),0,1));z=z0*(1-frac)+z1*frac
                if d0>=end-.001:
                    old=oldwalk.height(q)
                    if old is not None:z=old+.001
                return z
            emit(shape,height)
    if steps:
        for i,d0 in enumerate(risers,1):
            a,b=section(d0);z0=plateau+(target-plateau)*(i-1)/steps;z1=plateau+(target-plateau)*i/steps
            if pad.covers(Point((a+b)/2)):continue
            k=len(vv);vv.extend([[*a,z0],[*b,z0],[*b,z1],[*a,z1]]);ff.extend([[k,k+1,k+2],[k,k+2,k+3]]);mi.extend([1,1])
    ob=bpy.data.objects[w['name']];m=bpy.data.meshes.new(w['name']+'_sectioned');m.from_pydata(vv,[],ff);m.materials.append(bpy.data.materials['Road_Modular_Original_Atlas']);m.materials.append(bpy.data.materials['Bridge_Concrete']);m.polygons.foreach_set('material_index',np.array(mi,np.int32));m.update();uv=m.uv_layers.new(name='UVMap')
    for li,loop in enumerate(m.loops):
        q=m.vertices[loop.vertex_index].co;uv.data[li].uv=(.216+.055*((q.x/3)%1),.5989+.1777*((q.y/16.9048)%1))
    ob.data=m;w['profile_mesh']='ordered cross sections and explicit landings';print('ACCESS_REBUILT',w['name'],len(ff),'stairs',steps,flush=True)
(ROOT/'model/city_plan.json').write_text(json.dumps(p,separators=(',',':')));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/huizhou_road_network.blend'),compress=True)
