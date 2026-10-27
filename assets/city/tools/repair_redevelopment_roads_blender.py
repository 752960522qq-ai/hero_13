"""Locally rebuild four road junctions on the current editable city.

Road polygons and sidewalks are cut only inside the recorded repair boxes.
The replacement sidewalk uses the supplied Road Modular sidewalk atlas.
"""
from pathlib import Path
import argparse,copy,json,math,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--templates',type=Path,required=True);ap.add_argument('--shapely-path',type=Path);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from optimize_city_plan import asset_triangles,frame,clip_poly_y,smoothstep

bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));sc=bpy.context.scene;bpy.context.view_layer.update()
plan=json.loads(args.plan.read_text());scheme=json.loads(args.scheme.read_text())
patches=[box(*q) for q in scheme['patch_bounds']];patcharea=unary_union(patches)
oldfull=shapely.from_geojson(scheme['old_full_footprint']);newroad=shapely.from_geojson(scheme['new_pavement']);newfull=shapely.from_geojson(scheme['new_full_footprint'])
newwalk=newfull.difference(newroad);added_footprint=newfull.difference(oldfull).intersection(patcharea)

def clip_half(poly,axis,bound,keep_greater):
    if len(poly)==0:return []
    out=[]
    def signed(p):return (p[axis]-bound)*(1 if keep_greater else -1)
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=signed(a),signed(b);ia,ib=da>=-1e-9,db>=-1e-9
        if ia:out.append(a)
        if ia!=ib:
            t=da/(da-db);out.append(a+(b-a)*t)
    return out
def outside_rectangle(poly,r):
    xmin,ymin,xmax,ymax=r
    constraints=[(0,xmin,True),(0,xmax,False),(1,ymin,True),(1,ymax,False)]
    current=list(poly);parts=[]
    for axis,val,ge in constraints:
        outside=clip_half(current,axis,val,not ge)
        if len(outside)>=3:parts.append(outside)
        current=clip_half(current,axis,val,ge)
        if len(current)<3:break
    return parts
def fan(poly):
    return [np.asarray([poly[0],poly[i],poly[i+1]]) for i in range(1,len(poly)-1)]
def mesh_arrays(obj):
    m=obj.data
    co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    loops=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',loops)
    totals=np.empty(len(m.polygons),np.int32);m.polygons.foreach_get('loop_total',totals);assert np.all(totals==3),obj.name
    faces=loops.reshape(-1,3)
    uv=None
    if m.uv_layers.active:
        uv=np.empty(len(m.loops)*2,np.float32);m.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
    color=None
    if m.color_attributes.get('Color'):
        a=m.color_attributes['Color'];assert a.domain=='CORNER'
        color=np.empty(len(m.loops)*4,np.float32);a.data.foreach_get('color',color);color=color.reshape(-1,3,4)
    material=np.empty(len(m.polygons),np.int32);m.polygons.foreach_get('material_index',material)
    smooth=np.empty(len(m.polygons),np.bool_);m.polygons.foreach_get('use_smooth',smooth)
    return co,faces,uv,color,material,smooth
def attrs_for(i,co,faces,uv,color):
    arr=[co[faces[i]].astype(np.float64)]
    if uv is not None:arr.append(uv[i].astype(np.float64))
    if color is not None:arr.append(color[i].astype(np.float64))
    return np.concatenate(arr,axis=1)
def write_mesh(obj,co,faces,uv,color,material,smooth,kept,additions):
    if additions:
        points=np.asarray([q[0][:,:3] for q in additions],np.float32).reshape(-1,3)
        newfaces=np.arange(len(co),len(co)+len(points),dtype=np.int32).reshape(-1,3)
        co=np.vstack([co,points]);faceout=np.vstack([faces[kept],newfaces])
        ext=np.asarray([q[0][:,3:] for q in additions],np.float32)
        column=0
        if uv is not None:
            uv=np.concatenate([uv[kept],ext[:,:,column:column+2]],axis=0);column+=2
        if color is not None:color=np.concatenate([color[kept],ext[:,:,column:column+4]],axis=0)
        material=np.r_[material[kept],np.asarray([q[1] for q in additions],np.int32)]
        smooth=np.r_[smooth[kept],np.asarray([q[2] for q in additions],np.bool_)]
    else:
        faceout=faces[kept]
        if uv is not None:uv=uv[kept]
        if color is not None:color=color[kept]
        material=material[kept];smooth=smooth[kept]
    old=obj.data;name=old.name+'_LocalRepair';new=bpy.data.meshes.new(name)
    new.vertices.add(len(co));new.vertices.foreach_set('co',np.ascontiguousarray(co,dtype=np.float32).ravel())
    new.loops.add(len(faceout)*3);new.loops.foreach_set('vertex_index',np.ascontiguousarray(faceout,dtype=np.int32).ravel())
    new.polygons.add(len(faceout));new.polygons.foreach_set('loop_start',np.arange(len(faceout),dtype=np.int32)*3)
    new.polygons.foreach_set('loop_total',np.full(len(faceout),3,np.int32))
    new.polygons.foreach_set('material_index',np.ascontiguousarray(material,dtype=np.int32))
    new.polygons.foreach_set('use_smooth',np.ascontiguousarray(smooth,dtype=np.bool_))
    for mat in old.materials:new.materials.append(mat)
    if uv is not None:
        layer=new.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.ascontiguousarray(uv,dtype=np.float32).ravel())
    if color is not None:
        layer=new.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
        layer.data.foreach_set('color',np.ascontiguousarray(color,dtype=np.float32).ravel())
    new.update();obj.data=new
    if old.users==0:bpy.data.meshes.remove(old)
    return len(faceout)

def crop_rectangles(obj):
    co,faces,uv,color,material,smooth=mesh_arrays(obj)
    tri=co[faces];lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1);intersect=np.zeros(len(faces),bool);inside=np.zeros(len(faces),bool)
    for r in scheme['patch_bounds']:
        xmin,ymin,xmax,ymax=r
        i=(hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax)
        f=(lo[:,0]>=xmin)&(hi[:,0]<=xmax)&(lo[:,1]>=ymin)&(hi[:,1]<=ymax)
        intersect|=i;inside|=f
    additions=[]
    for i in np.flatnonzero(intersect&~inside):
        initial=attrs_for(i,co,faces,uv,color);parts=[list(initial)]
        for r in scheme['patch_bounds']:
            xmin,ymin,xmax,ymax=r
            if hi[i,0]<xmin or lo[i,0]>xmax or hi[i,1]<ymin or lo[i,1]>ymax:continue
            parts=[sub for part in parts for sub in outside_rectangle(part,r)]
        for part in parts:
            for t in fan(part):
                if np.linalg.norm(np.cross(t[1,:3]-t[0,:3],t[2,:3]-t[0,:3]))>1e-10:
                    additions.append((t,int(material[i]),bool(smooth[i])))
    count=write_mesh(obj,co,faces,uv,color,material,smooth,~intersect,additions)
    print('CROP_RECT',obj.name,'removed',int(intersect.sum()),'new_faces',count,'split_faces',len(additions),flush=True)

def clip_ground(obj,cutter):
    if cutter.is_empty:return
    co,faces,uv,color,material,smooth=mesh_arrays(obj)
    tri=co[faces];lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1)
    xmin,ymin,xmax,ymax=cutter.bounds
    candidate=np.flatnonzero((hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax))
    polys=shapely.polygons(tri[candidate,:,:2]);valid=shapely.area(polys)>1e-9
    validids=candidate[valid];polys=polys[valid]
    selected=shapely.intersects(cutter,polys);ids=validids[selected];polys=polys[selected]
    kept=np.ones(len(faces),bool);kept[ids]=False;additions=[]
    for i,poly in zip(ids,polys):
        remainder=shapely.difference(poly,cutter)
        if remainder.is_empty or remainder.area<1e-10:continue
        a=attrs_for(i,co,faces,uv,color)
        A=a[0,:2];u=a[1,:2]-A;v=a[2,:2]-A;det=u[0]*v[1]-u[1]*v[0]
        for part in shapely.get_parts(shapely.constrained_delaunay_triangles(remainder)):
            if part.is_empty or part.area<1e-10:continue
            xy=np.asarray(part.exterior.coords)[:3,:2];d=xy-A
            s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det
            weights=np.c_[1-s-t,s,t];attrs=weights@a
            cross=(attrs[1,0]-attrs[0,0])*(attrs[2,1]-attrs[0,1])-(attrs[1,1]-attrs[0,1])*(attrs[2,0]-attrs[0,0])
            if cross<0:attrs=attrs[::-1]
            additions.append((attrs,int(material[i]),bool(smooth[i])))
    count=write_mesh(obj,co,faces,uv,color,material,smooth,kept,additions)
    print('CLIP_GROUND',obj.name,'touched',len(ids),'new_faces',count,flush=True)

for name in ['MAIN_Road_Modular_Repaired','Continuous_Pavement_Repaired','MAIN_Sidewalk_Modular_Continuous','Sidewalk_Continuous_Transition_Base']:
    crop_rectangles(bpy.data.objects[name])
for name in ['MAIN_Sculpted_Terrain','CBD_Conforming_Concrete_Paving']:
    clip_ground(bpy.data.objects[name],added_footprint)

segments=[];sa=[];sb=[];za=[];zb=[];half=[]
for e in plan['edges']:
    q=np.asarray(e['points']);sa.extend(q[:-1,:2]);sb.extend(q[1:,:2]);za.extend(q[:-1,2]);zb.extend(q[1:,2]);half.extend([e['carriage_width']/2]*len(q[:-1]))
sa=np.asarray(sa);sb=np.asarray(sb);delta=sb-sa;za=np.asarray(za);zb=np.asarray(zb);half=np.asarray(half)
tree=cKDTree((sa+sb)/2)
def project(co):
    co=np.asarray(co).reshape(-1,2);_,ids=tree.query(co,k=12);d=delta[ids]
    t=np.clip(np.sum((co[:,None,:]-sa[ids])*d,axis=-1)/np.maximum(np.sum(d*d,axis=-1),1e-12),0,1)
    points=sa[ids]+d*t[:,:,None];j=np.argmin(np.linalg.norm(co[:,None,:]-points,axis=-1),axis=1);row=np.arange(len(co));idx=ids[row,j];tt=t[row,j]
    return za[idx]+(zb[idx]-za[idx])*tt,idx,tt
def make_surface(name,shape,mat,parent,z_offset,source_uv=False,vertex_color=None):
    shape=shapely.segmentize(shape,3)
    tris=[g for g in shapely.get_parts(shapely.constrained_delaunay_triangles(shape)) if not g.is_empty and g.area>1e-9]
    if not tris:return None
    xy=np.array([np.asarray(t.exterior.coords)[:3,:2] for t in tris]);a=xy[:,1]-xy[:,0];b=xy[:,2]-xy[:,0]
    bad=a[:,0]*b[:,1]-a[:,1]*b[:,0]<0;xy[bad]=xy[bad][:,::-1,:]
    flat=xy.reshape(-1,2);z,ids,t=project(flat);verts=np.c_[flat,z+z_offset];faces=np.arange(len(verts),dtype=np.int32).reshape(-1,3)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts.tolist(),[],faces.tolist());mesh.materials.append(mat);mesh.update()
    obj=bpy.data.objects.new(name,mesh);sc.collection.objects.link(obj);obj.parent=parent
    if source_uv:
        q=sa[ids]+delta[ids]*t[:,None];across=np.clip((np.linalg.norm(flat-q,axis=1)-half[ids])/3,0,1)
        unit=delta[ids]/np.maximum(np.linalg.norm(delta[ids],axis=1,keepdims=True),1e-9)
        along=np.mod(np.sum(q*unit,axis=1),16.9048)/16.9048
        u=.271-.055*across;v=.7766-.1777*along
        layer=mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.c_[u,v].astype(np.float32).ravel())
    if vertex_color:
        layer=mesh.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
        layer.data.foreach_set('color',np.tile(np.array(vertex_color,np.float32),(len(mesh.loops),1)).ravel())
    return obj

root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout']
group=bpy.data.objects.new('12_REPAIRED_JUNCTIONS',None);sc.collection.objects.link(group);group.parent=root
roadmat=bpy.data.materials['Junction_Asphalt.001'];walkmat=bpy.data.materials['Road_Modular_Original_Atlas.001'];landmat=bpy.data.materials['MAIN_Terrain.001']
road=make_surface('Junction_Repairs_Asphalt',newroad.intersection(patcharea),roadmat,group,-.008);road['driveable']=True
walk=make_surface('Junction_Repairs_Sidewalk_OriginalAtlas',newwalk.intersection(patcharea),walkmat,group,.143577,True);walk['walkable']=True;walk['width_m']=3.0
walk['source_mesh']='Road Modular sidewalk surface and original UV atlas, remeshed at repaired junctions'
fill=make_surface('Junction_Repairs_Ground_Infill',oldfull.difference(newfull).intersection(patcharea),landmat,group,-.08,False,(.19,.28,.115,1))

# Restore actual kit road surfaces and lane markings up to the junction mouths.
templates=json.loads(args.templates.read_text())
prepared={k:asset_triangles(templates[k],k) for k in ['local','arterial']}
road_vertices=[];road_uv=[]
for e in plan['edges']:
    if e['region']!='MAIN':continue
    line=LineString(np.asarray(e['points'])[:,:2])
    if not line.buffer(e['width']/2+2).intersects(patcharea):continue
    start,stop=e['range']
    if stop-start<.05:continue
    kind='arterial' if e['original_width']>=20 else 'local'
    triangles,period,sourcehalf=prepared[kind];scale=e['carriage_width']/(sourcehalf*2)
    chunks=[]
    for tile in np.arange(start,stop-.01,period):
        avail=min(period,stop-tile)
        if avail>period-.001:
            q=np.array(triangles);q[:,:,1]+=tile;chunks.append(q);continue
        for tri in triangles:
            part=clip_poly_y(tri,avail,False)
            if len(part)<3:continue
            for k in range(1,len(part)-1):
                q=part[[0,k,k+1]].copy();q[:,1]+=tile;chunks.append(q[None,:,:])
    if not chunks:continue
    q=np.concatenate(chunks);flat=q.reshape(-1,5);dist=flat[:,1];pos,norm=frame(e,dist)
    pos[:,:2]+=norm*(flat[:,0]*scale)[:,None]
    median=np.abs(flat[:,0])<2.0;taper=smoothstep(np.minimum(dist-start,stop-dist)/18)
    z=flat[:,2].copy();z[median]*=taper[median];pos[:,2]+=z
    data=np.concatenate([pos,flat[:,3:]],axis=1).reshape(-1,3,5)[:,::-1,:]
    for tri in data:
        lo=tri[:,:2].min(0);hi=tri[:,:2].max(0)
        for r in scheme['patch_bounds']:
            xmin,ymin,xmax,ymax=r
            if hi[0]<xmin or lo[0]>xmax or hi[1]<ymin or lo[1]>ymax:continue
            part=list(tri)
            for axis,bound,ge in [(0,xmin,True),(0,xmax,False),(1,ymin,True),(1,ymax,False)]:
                part=clip_half(part,axis,bound,ge)
                if len(part)<3:break
            for t in fan(part):
                if np.linalg.norm(np.cross(t[1,:3]-t[0,:3],t[2,:3]-t[0,:3]))>1e-10:
                    road_vertices.extend(t[:,:3]);road_uv.extend(t[:,3:])
if road_vertices:
    rv=np.array(road_vertices,np.float32);ruv=np.array(road_uv,np.float32);rf=np.arange(len(rv),dtype=np.int32).reshape(-1,3)
    m=bpy.data.meshes.new('Junction_Repairs_Original_Road_Kit');m.from_pydata(rv.tolist(),[],rf.tolist());m.materials.append(walkmat);m.update()
    o=bpy.data.objects.new('Junction_Repairs_Original_Road_Kit',m);sc.collection.objects.link(o);o.parent=group
    layer=m.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',ruv.ravel())
    o['driveable']=True;o['source_mesh']='Road Modular original road and double-road geometry, UVs and materials'

# Curbs at real sidewalk boundaries only, excluding artificial patch box edges.
vv=[];ff=[];uv=[]
for r in scheme['patch_bounds']:
    region=box(*r);local=shapely.segmentize(newwalk.intersection(region),3)
    for poly in shapely.get_parts(local):
        if poly.geom_type!='Polygon':continue
        for ring in [poly.exterior,*poly.interiors]:
            xy=np.asarray(ring.coords)
            for a,b in zip(xy[:-1],xy[1:]):
                if region.boundary.distance(LineString([a,b]).interpolate(.5,normalized=True))<.001:continue
                z,_,_=project([a,b]);off=len(vv)
                vv.extend([[*a,z[0]+.143577],[*b,z[1]+.143577],[*b,z[1]-.06],[*a,z[0]-.06]])
                ff.extend([[off,off+1,off+2],[off,off+2,off+3]]);uv.extend([(.216,.67),(.216,.69),(.216,.69),(.216,.67)])
if ff:
    m=bpy.data.meshes.new('Junction_Repair_Curbs');m.from_pydata(vv,[],ff);m.materials.append(walkmat);m.update()
    o=bpy.data.objects.new('Junction_Repair_Curbs',m);sc.collection.objects.link(o);o.parent=group
    layer=m.uv_layers.new(name='UVMap');ids=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',ids);layer.data.foreach_set('uv',np.array(uv,np.float32)[ids].ravel())

# Mark individual junction approaches; lines are separate and replaceable.
paint=bpy.data.materials.new('Road_Marking_White');paint.diffuse_color=(.82,.83,.8,1);paint.use_nodes=True
paint.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.82,.83,.8,1)
mark_v=[];mark_f=[];crosswalks=[]
for repair in scheme['repairs']:
    target=np.array(repair['node_xy']);nid=min(range(len(plan['nodes'])),key=lambda i:np.linalg.norm(np.array(plan['nodes'][i]['xy'])-target))
    node=plan['nodes'][nid]
    for eid in node['edges']:
        e=plan['edges'][eid]
        if e['bridge']:continue
        q=np.array(e['points'])
        if e['b']==nid:q=q[::-1]
        dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
        pos=min(node['radius']+2,dist[-1]*.35)
        if pos<6:continue
        point=np.array([np.interp(pos,dist,q[:,i]) for i in range(3)])
        h=.5;minus=np.array([np.interp(max(0,pos-h),dist,q[:,i]) for i in range(2)])
        plus=np.array([np.interp(min(dist[-1],pos+h),dist,q[:,i]) for i in range(2)])
        direction=plus-minus;direction/=max(np.linalg.norm(direction),1e-9);normal=np.array([-direction[1],direction[0]])
        count=0
        for offset in np.arange(-e['carriage_width']/2+.8,e['carriage_width']/2-.4,1.1):
            if e['carriage_width']>15 and abs(offset)<1.4:continue
            center=point[:2]+normal*offset
            xy=np.array([center-direction*1.65-normal*.27,center+direction*1.65-normal*.27,
                         center+direction*1.65+normal*.27,center-direction*1.65+normal*.27])
            if not newroad.buffer(-.05).covers(Polygon(xy)) or not patcharea.covers(Polygon(xy)):continue
            z,_,_=project(xy);off=len(mark_v);mark_v.extend(np.c_[xy,z+.018].tolist());mark_f.append([off,off+1,off+2,off+3]);count+=1
        if count:crosswalks.append({'node':nid,'edge':e['name'],'stripes':count})
if mark_f:
    m=bpy.data.meshes.new('Repair_Crosswalks');m.from_pydata(mark_v,[],mark_f);m.materials.append(paint);m.update()
    o=bpy.data.objects.new('Repair_Crosswalk_Markings',m);sc.collection.objects.link(o);o.parent=group

bpy.context.view_layer.update();args.out.mkdir(parents=True,exist_ok=True)
report={'repairs':scheme['repairs'],'crosswalks':crosswalks,'new_road_area_m2':added_footprint.area,
        'old_terrain_infill_m2':oldfull.difference(newfull).intersection(patcharea).area}
(args.out/'road_repairs.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'roads_repaired.blend').resolve()),compress=True)
print('LOCAL_ROAD_REPAIRS_COMPLETE',json.dumps({'junctions':len(scheme['repairs']),'crosswalks':len(crosswalks),'new_area':added_footprint.area}),flush=True)
