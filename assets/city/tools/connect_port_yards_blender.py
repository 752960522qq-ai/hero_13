"""Connect blockout container yards to real roads with graded service drives.

Road Modular sidewalk material is retained across and beside each driveway.
The sidewalk is clipped at the entrance instead of leaving a raised curb across
the live traffic lane; the connection is also represented in the road graph.
"""
from pathlib import Path
import argparse,json,math,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--districts',type=Path,required=True);ap.add_argument('--shapely-path',type=Path);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Point,Polygon,LineString
from shapely.ops import nearest_points,unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));bpy.context.view_layer.update()
sc=bpy.context.scene;plan=json.loads(args.plan.read_text());district=json.loads(args.districts.read_text())
terrain=HeightField([bpy.data.objects['EAST_Sculpted_Terrain']])
walkobjs=[bpy.data.objects['EAST_Sidewalk_Modular_Continuous'],bpy.data.objects['Sidewalk_Continuous_Transition_Base']]
roadobjs=[bpy.data.objects['EAST_Road_Modular_Repaired'],bpy.data.objects['Continuous_Pavement_Repaired']]
def triangles(obj,bounds):
    m=obj.data;m.calc_loop_triangles()
    co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co)
    co=co.reshape(-1,3).astype(np.float64);M=np.asarray(obj.matrix_world,np.float64);co=co@M[:3,:3].T+M[:3,3]
    ids=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',ids);tri=co[ids.reshape(-1,3)]
    lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1);xmin,ymin,xmax,ymax=bounds
    tri=tri[(hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax)]
    a=tri[:,1,:2]-tri[:,0,:2];b=tri[:,2,:2]-tri[:,0,:2];return tri[(a[:,0]*b[:,1]-a[:,1]*b[:,0])>1e-8]
class LocalField:
    def __init__(self,objs,bounds):
        tri=np.concatenate([triangles(o,bounds) for o in objs]);self.tri=tri
        xy=tri[:,:,:2].reshape(-1,2);uni,ids=np.unique(xy,axis=0,return_inverse=True)
        self.tree=BVHTree.FromPolygons(np.c_[uni,np.zeros(len(uni))].tolist(),ids.reshape(-1,3).tolist(),all_triangles=True)
    def height(self,xy):
        xy=np.asarray(xy[:2],float);out=[]
        for _,_,i,_ in self.tree.find_nearest_range(Vector((float(xy[0]),float(xy[1]),0)),.002):
            t=self.tri[i];a=t[0,:2];u=t[1,:2]-a;v=t[2,:2]-a;d=xy-a;det=u[0]*v[1]-u[1]*v[0]
            s=(d[0]*v[1]-d[1]*v[0])/det;q=(u[0]*d[1]-u[1]*d[0])/det
            if min(1-s-q,s,q)>=-1e-7:out.append((1-s-q)*t[0,2]+s*t[1,2]+q*t[2,2])
        return None if not out else float(max(out))

occupied=unary_union([Polygon(b['footprint']).buffer(2) for b in plan['buildings']]
  +[Polygon(b['footprint_xy']).buffer(2) for b in plan['real_buildings']])
drives=[];reserved=[]
for yard in district['east_container_yards']:
    x,y=yard['center'];w,d=yard['size'];yardpoly=Polygon(yard['footprint'])
    starts=[(np.array([x-w/2,y+1.5]),np.array([-1,0])),(np.array([x+w/2,y+1.5]),np.array([1,0])),
            (np.array([x,y-d/2]),np.array([0,-1])),(np.array([x,y+d/2]),np.array([0,1]))]
    options=[]
    for side,(start,outward) in enumerate(starts):
        # Container stacks leave an east-west aisle at y + 1.5 m; avoid
        # connecting through the packed north and south edges of the yard.
        if side >= 2: continue
        for eid,e in enumerate(plan['edges']):
            if e['region']!='EAST' or e['bridge'] or e['name'].startswith('E_PORT_Service_'):continue
            pp=np.asarray(e['points']);line=LineString(pp[:,:2]);q=np.array(nearest_points(Point(start),line)[1].coords[0])
            vec=q-start;distance=np.linalg.norm(vec)
            if not e['width']/2+4<distance<100:continue
            unit=vec/distance
            if unit@outward<.25:continue
            proj=line.project(Point(q))
            if proj<25 or line.length-proj<25:continue
            end=q-unit*(e['carriage_width']/2-.8);start_in=start-unit*.8;length=float(np.linalg.norm(end-start_in))
            corridor=LineString([start_in,end]).buffer(4.6,cap_style='flat')
            if corridor.intersects(occupied) or any(corridor.intersects(g) for g in reserved):continue
            if any(corridor.intersects(Polygon(z['footprint'])) for z in district['east_container_yards'] if z['name']!=yard['name']):continue
            ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pp[:,:2],axis=0),axis=1))];roadz=float(np.interp(proj,ds,pp[:,2]))
            grade=abs(roadz-yard['foundation_top_m'])/length
            if grade>.08:continue
            score=length*2+grade*200+(20 if side>=2 else 0)
            options.append((score,eid,start_in,end,q,unit,roadz,proj))
    options.sort(key=lambda x:x[0]);chosen=None;failures=[]
    for score,eid,start,end,q,unit,roadz,proj in options[:15]:
        normal=np.array([-unit[1],unit[0]]);e=plan['edges'][eid]
        walkcenter=q-unit*(e['carriage_width']/2+1.5)
        points=np.vstack([start,end,walkcenter]);lo=points.min(0)-12;hi=points.max(0)+12
        bounds=[lo[0],lo[1],hi[0],hi[1]]
        try:
            wf=LocalField(walkobjs,bounds);rf=LocalField(roadobjs,bounds)
            offsets=np.linspace(-3,3,7)
            walkvalues=np.array([wf.height(walkcenter+normal*k) if wf.height(walkcenter+normal*k) is not None else np.nan for k in offsets])
            roadvalues=np.array([rf.height(end+normal*k) if rf.height(end+normal*k) is not None else np.nan for k in offsets])
            if not np.isfinite(walkvalues).all() or not np.isfinite(roadvalues).all():raise ValueError('source sidewalk or road is not fully sampled')
            length=float(np.linalg.norm(end-start));at_walk=float(np.dot(walkcenter-start,unit))
            if not 1<at_walk<length-1.5:raise ValueError('no room for the curb transition')
            stations=np.unique(np.r_[np.linspace(0,length,int(math.ceil(length/.6))+1),at_walk])
            xy=start[None,None,:]+stations[:,None,None]*unit[None,None,:]+offsets[None,:,None]*normal[None,None,:]
            ground=np.array([[terrain.height(p) if terrain.height(p) is not None else np.nan for p in row] for row in xy])
            mid=float(walkvalues.mean());endheight=float(roadvalues.mean())
            desired=np.interp(stations,[0,at_walk,length],[yard['foundation_top_m']+.004,mid+.004,endheight+.004])
            cross=np.zeros((len(stations),len(offsets)))
            left=np.clip(stations/at_walk,0,1);right=np.clip((length-stations)/(length-at_walk),0,1)
            blend=np.minimum(left,right)
            cross=blend[:,None]*(walkvalues-mid)[None,:]+(1-right)[:,None]*(roadvalues-endheight)[None,:]
            required=np.max(np.where(np.isfinite(ground),ground-cross+.025,-1e6),axis=1)
            height=np.maximum(desired,required)
            for k in range(1,len(height)):height[k]=max(height[k],height[k-1]-.08*(stations[k]-stations[k-1]))
            for k in range(len(height)-2,-1,-1):height[k]=max(height[k],height[k+1]-.08*(stations[k+1]-stations[k]))
            wi=int(np.argmin(np.abs(stations-at_walk)))
            if abs(height[0]-desired[0])>.015 or abs(height[-1]-desired[-1])>.015 or abs(height[wi]-desired[wi])>.015:
                raise ValueError('terrain prevents a smooth approach at both connections')
            zz=height[:,None]+cross
            grade=float(np.max(np.abs(np.diff(zz,axis=0))/np.diff(stations)[:,None]))
            if grade>.084:raise ValueError('driveway grade too steep')
            corridor=LineString([start,end]).buffer(4.6,cap_style='flat')
            chosen={'yard':yard,'edge_index':eid,'edge':e,'start':start,'end':end,'q':q,'unit':unit,'normal':normal,
                    'roadz':roadz,'stations':stations,'at_walk':at_walk,'xy':xy,'z':zz,'ground':ground,
                    'walk_z':walkvalues,'road_z':roadvalues,'grade':grade,'proj':proj,'corridor':corridor}
            break
        except (ValueError,IndexError) as err:
            failures.append(str(err))
    if chosen is None:raise RuntimeError('No safe road access for '+yard['name']+': '+str(failures[:5]))
    drives.append(chosen);reserved.append(chosen['corridor'])
    print('PORT_ACCESS_PREFLIGHT',yard['name'],chosen['edge']['name'],'grade',chosen['grade'],'length',float(chosen['stations'][-1]),flush=True)
assert len({drive['edge_index'] for drive in drives}) == len(drives), 'Service drives must split distinct public edges'

def half_clip(poly,axis,bound,ge):
    out=[]
    def dist(p):return (p[axis]-bound)*(1 if ge else -1)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=dist(a),dist(b);ia,ib=da>=-1e-9,db>=-1e-9
        if ia:out.append(a)
        if ia!=ib:out.append(a+(b-a)*da/(da-db))
    return out
def outside_box(poly,bounds):
    cur=list(poly);pieces=[]
    for axis,bound,ge in [(0,bounds[0],True),(0,bounds[1],False),(1,bounds[2],True),(1,bounds[3],False)]:
        out=half_clip(cur,axis,bound,not ge)
        if len(out)>=3:pieces.append(out)
        cur=half_clip(cur,axis,bound,ge)
        if len(cur)<3:break
    return pieces
def trim_sidewalk(obj):
    old=obj.data;n=len(old.polygons)
    co=np.empty(len(old.vertices)*3,np.float32);old.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    ids=np.empty(len(old.loops),np.int32);old.loops.foreach_get('vertex_index',ids);faces=ids.reshape(-1,3)
    totals=np.empty(n,np.int32);old.polygons.foreach_get('loop_total',totals);assert np.all(totals==3)
    uv=np.empty(len(old.loops)*2,np.float32);old.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
    mats=np.empty(n,np.int32);old.polygons.foreach_get('material_index',mats)
    smooth=np.empty(n,np.bool_);old.polygons.foreach_get('use_smooth',smooth)
    pts=co[faces];removed=np.zeros(n,bool);partial=[];frames=[]
    for drive in drives:
        start=drive['start'];u=drive['unit'];v=drive['normal'];length=drive['stations'][-1]
        delta=pts[:,:,:2]-start;localx=delta@u;localy=delta@v
        lo=np.c_[localx.min(1),localy.min(1)];hi=np.c_[localx.max(1),localy.max(1)]
        touched=(hi[:,0]>=0)&(lo[:,0]<=length)&(hi[:,1]>=-3)&(lo[:,1]<=3)
        inside=(lo[:,0]>=0)&(hi[:,0]<=length)&(lo[:,1]>=-3)&(hi[:,1]<=3)
        frames.append((drive,touched,inside));removed|=touched
    for drive,touched,inside in frames:
        start=drive['start'];u=drive['unit'];v=drive['normal'];length=drive['stations'][-1]
        for i in np.flatnonzero(touched&~inside):
            p=pts[i].astype(np.float64);delta=p[:,:2]-start
            local=np.c_[delta@u,delta@v,p,uv[i]]
            for part in outside_box(local,[0,length,-3,3]):
                for j in range(1,len(part)-1):
                    tri=np.asarray([part[0],part[j],part[j+1]])
                    if np.linalg.norm(np.cross(tri[1,2:5]-tri[0,2:5],tri[2,2:5]-tri[0,2:5]))>1e-10:partial.append((tri,int(mats[i]),bool(smooth[i])))
    kept=~removed
    if partial:
        more=np.asarray([p[0] for p in partial]);vnew=more[:,:,2:5].reshape(-1,3).astype(np.float32)
        fnew=np.arange(len(co),len(co)+len(vnew),dtype=np.int32).reshape(-1,3)
        allco=np.vstack([co,vnew]);allfaces=np.vstack([faces[kept],fnew]);alluv=np.concatenate([uv[kept],more[:,:,5:7]],axis=0)
        allmats=np.r_[mats[kept],[p[1] for p in partial]];allsmooth=np.r_[smooth[kept],[p[2] for p in partial]]
    else:
        allco=co;allfaces=faces[kept];alluv=uv[kept];allmats=mats[kept];allsmooth=smooth[kept]
    m=bpy.data.meshes.new(old.name+'_PortEntrances');m.vertices.add(len(allco));m.vertices.foreach_set('co',np.ascontiguousarray(allco,np.float32).ravel())
    m.loops.add(len(allfaces)*3);m.loops.foreach_set('vertex_index',np.ascontiguousarray(allfaces,np.int32).ravel())
    m.polygons.add(len(allfaces));m.polygons.foreach_set('loop_start',np.arange(len(allfaces),dtype=np.int32)*3)
    m.polygons.foreach_set('loop_total',np.full(len(allfaces),3,np.int32));m.polygons.foreach_set('material_index',np.asarray(allmats,np.int32))
    m.polygons.foreach_set('use_smooth',np.asarray(allsmooth,np.bool_))
    for mat in old.materials:m.materials.append(mat)
    layer=m.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.ascontiguousarray(alluv,np.float32).ravel());m.update()
    obj.data=m
    if old.users==0:bpy.data.meshes.remove(old)
    print('PORT_CURB_CUT',obj.name,'faces_touched',int(removed.sum()),flush=True)
for obj in walkobjs:trim_sidewalk(obj)

root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout']
group=bpy.data.objects.new('19_PORT_SERVICE_ACCESS',None);sc.collection.objects.link(group);group.parent=root
roadmat=bpy.data.materials['Junction_Asphalt.001'];walkmat=bpy.data.materials['Road_Modular_Original_Atlas.001']
records=[]
for i,drive in enumerate(drives):
    xy=drive['xy'];z=drive['z'];stations=drive['stations'];n,cols=z.shape
    floor=min(float(np.nanmin(drive['ground'])),float(z.min()))-.3
    v=np.dstack([xy,z]).reshape(-1,3).tolist()+np.dstack([xy,np.full_like(z,floor)]).reshape(-1,3).tolist()
    faces=[];materials=[];nv=n*cols
    for k in range(n-1):
        for j in range(cols-1):
            a=k*cols+j;b=(k+1)*cols+j
            for face in [[a,b,b+1],[a,b+1,a+1]]:
                faces.append(face);materials.append(1 if abs((stations[k]+stations[k+1])/2-drive['at_walk'])<1.5 else 0)
                faces.append([q+nv for q in face[::-1]]);materials.append(0)
    ring=list(range(cols))+[j*cols+cols-1 for j in range(1,n)]+list(range(nv-2,nv-cols-1,-1))+[j*cols for j in range(n-2,0,-1)]
    for a,b in zip(ring,ring[1:]+ring[:1]):faces.append([a,b,b+nv,a+nv]);materials.append(0)
    m=bpy.data.meshes.new('Port_Service_Drive_%02d'%i);m.from_pydata(v,[],faces);m.materials.append(roadmat);m.materials.append(walkmat);m.update()
    m.polygons.foreach_set('material_index',np.array(materials,np.int32))
    obj=bpy.data.objects.new('Port_Service_Drive_%02d'%i,m);sc.collection.objects.link(obj);obj.parent=group;obj['driveable']=True;obj['yard']=drive['yard']['name']
    layer=m.uv_layers.new(name='UVMap');ids=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',ids);coords=np.array(v)
    uv=np.c_[.216+.055*np.mod(coords[:,0]/5,1),.599+.1777*np.mod(coords[:,1]/16.9048,1)]
    layer.data.foreach_set('uv',uv[ids].astype(np.float32).ravel())
    # 1.5 m sidewalks run on each side, meeting the original sidewalk at grade.
    for side in [-1,1]:
        vv=[];ff=[]
        for k,s in enumerate(stations):
            base=drive['start']+drive['unit']*s
            rise=.14*min(1,max(0,(drive['at_walk']-s)/3))
            zz=float(z[k,0 if side<0 else -1])+rise
            for off in [3,4.5]:vv.append([*(base+drive['normal']*side*off),zz])
        for k in range(n-1):
            a=2*k;b=2*k+2
            ff.extend([[a,b,b+1],[a,b+1,a+1]] if side>0 else [[a,b+1,b],[a,a+1,b+1]])
        m2=bpy.data.meshes.new('Port_Service_Walk_%02d_%s'%(i,side));m2.from_pydata(vv,[],ff);m2.materials.append(walkmat);m2.update()
        o=bpy.data.objects.new(m2.name,m2);sc.collection.objects.link(o);o.parent=group;o['walkable']=True;o['width_m']=1.5;o['source_material']='Road Modular sidewalk atlas'
        uv2=m2.uv_layers.new(name='UVMap');ids=np.empty(len(m2.loops),np.int32);m2.loops.foreach_get('vertex_index',ids)
        vv=np.array(vv);arr=np.c_[.216+.055*np.mod(vv[:,0]/5,1),.599+.1777*np.mod(vv[:,1]/16.9048,1)]
        uv2.data.foreach_set('uv',arr[ids].astype(np.float32).ravel())

    # Split the existing public edge at the actual meeting point and attach a
    # service edge; all graph nodes reference identical endpoint elevations.
    e=drive['edge'];eid=drive['edge_index'];points=np.array(e['points']);xy0=drive['q'];proj=drive['proj']
    ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1))]
    j=int(np.searchsorted(ds,proj));assert 0<j<len(points)
    q3=np.array([xy0[0],xy0[1],drive['roadz']]);first=np.vstack([points[:j],q3]);second=np.vstack([q3,points[j:]])
    junction=len(plan['nodes']);plan['nodes'].append({'xy':xy0.tolist(),'z':drive['roadz'],'radius':8.,'edges':[]})
    yardnode=len(plan['nodes']);start=drive['start'];plan['nodes'].append({'xy':start.tolist(),'z':float(z[0].mean()),'radius':4.,'edges':[]})
    def split_record(points,a,b):
        rec=dict(e);rec['points']=points.tolist();rec['a']=a;rec['b']=b
        dd=np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1);rec['length']=float(dd.sum());rec['max_grade']=float(np.max(np.abs(np.diff(points[:,2]))/dd))
        rec['range']=[min(plan['nodes'][a]['radius'],rec['length']*.42),rec['length']-min(plan['nodes'][b]['radius'],rec['length']*.42)]
        return rec
    orig_a,orig_b=e['a'],e['b'];plan['edges'][eid]=split_record(first,orig_a,junction)
    plan['edges'].append(split_record(second,junction,orig_b))
    mid=np.c_[drive['xy'][:,3,:],np.mean(z,axis=1)];roadpoints=np.vstack([mid,q3])
    seg=np.linalg.norm(np.diff(roadpoints[:,:2],axis=0),axis=1)
    access={'name':'E_PORT_Service_%02d'%i,'region':'EAST','bridge':False,'original_width':9.,'carriage_width':6.,
            'sidewalk_width':1.5,'width':9.,'a':yardnode,'b':junction,'points':roadpoints.tolist(),
            'length':float(seg.sum()),'range':[0.,float(seg.sum())],'max_grade':float(np.max(np.abs(np.diff(roadpoints[:,2]))/seg))}
    plan['edges'].append(access)
    rec={'yard':drive['yard']['name'],'connects_to':e['name'],'service_edge':access['name'],'start_xy':start.tolist(),'end_xy':drive['end'].tolist(),
         'road_junction_xy':xy0.tolist(),'walk_center_xy':(drive['start']+drive['unit']*drive['at_walk']).tolist(),'length_m':float(stations[-1]),
         'drive_width_m':6.,'sidewalk_width_m':1.5,'maximum_grade':drive['grade'],
         'walk_end_max_lip_m':float(np.max(np.abs(z[np.argmin(np.abs(stations-drive['at_walk']))]-drive['walk_z']))),
         'road_end_max_lip_m':float(np.max(np.abs(z[-1]-drive['road_z'])))}
    records.append(rec)
for node in plan['nodes']:node['edges']=[]
for i,e in enumerate(plan['edges']):plan['nodes'][e['a']]['edges'].append(i);plan['nodes'][e['b']]['edges'].append(i)
plan['stats']['road_edges']=len(plan['edges']);plan['stats']['junctions']=sum(len(n['edges'])>=3 for n in plan['nodes'])
plan['stats']['road_length_m']=sum(e['length'] for e in plan['edges']);plan['stats']['maximum_road_grade']=max(e['max_grade'] for e in plan['edges'])
plan['stats']['port_service_drives']=len(records);plan['port_service_access']=records
args.out.mkdir(parents=True,exist_ok=True);(args.out/'city_plan.json').write_text(json.dumps(plan,separators=(',',':')))
(args.out/'port_access.json').write_text(json.dumps(records,indent=2))
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'connected_city.blend').resolve()),compress=True)
print('PORT_ACCESS_COMPLETE',json.dumps(records),flush=True)
