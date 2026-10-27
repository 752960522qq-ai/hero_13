"""Apply the CBD paving/infill and two old-town apartment assets to a city.

The input must be the editable city that already includes the two CBD assets.
Road, sidewalk and original terrain meshes are checked for unchanged geometry.
"""
from pathlib import Path
import argparse, hashlib, json, math, sys, gc
import bpy, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ap=argparse.ArgumentParser()
ap.add_argument('--blend',type=Path,required=True)
ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--candidates',type=Path,required=True)
ap.add_argument('--apartment-2',type=Path,required=True)
ap.add_argument('--apartment-3',type=Path,required=True)
ap.add_argument('--pavers',type=Path,required=True)
ap.add_argument('--shapely-path',type=Path)
ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField

args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
sc=bpy.context.scene;bpy.context.view_layer.update()
plan=json.loads(args.plan.read_text());data=json.loads(args.candidates.read_text())
root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout']
assert len(plan['real_buildings'])==2 and not bpy.data.objects.get('09_OLDTOWN_REAL_BUILDINGS')

def below(o,name):
    while o:
        if o.name==name:return True
        o=o.parent
    return False

def fingerprint(objects):
    h=hashlib.sha256()
    for o in sorted(objects,key=lambda o:o.name):
        h.update(o.name.encode())
        a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        ids=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',ids);h.update(ids.tobytes())
        h.update(np.array(o.matrix_world,np.float32).tobytes())
        if o.data.uv_layers.active:
            uv=np.empty(len(o.data.loops)*2,np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv);h.update(uv.tobytes())
    return h.hexdigest()

protected=[o for o in sc.objects if o.type=='MESH' and any(below(o,n) for n in ['01_TERRAIN','03_ROAD_NETWORK','06_SIDEWALKS'])]
before=fingerprint(protected)
terrain_obj=bpy.data.objects['MAIN_Sculpted_Terrain']
terrain=HeightField([terrain_obj])

def object_triangles(obj, bounds=None):
    mesh=obj.data;mesh.calc_loop_triangles()
    co=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',co)
    co=co.reshape(-1,3).astype(np.float64);m=np.array(obj.matrix_world,np.float64)
    co=co@m[:3,:3].T+m[:3,3]
    faces=np.empty(len(mesh.loop_triangles)*3,np.int32);mesh.loop_triangles.foreach_get('vertices',faces)
    faces=faces.reshape(-1,3);tri=co[faces]
    if bounds:
        xmin,ymin,xmax,ymax=bounds
        lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1)
        tri=tri[(hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax)]
    a=tri[:,1,:2]-tri[:,0,:2];b=tri[:,2,:2]-tri[:,0,:2]
    return tri[(a[:,0]*b[:,1]-a[:,1]*b[:,0])>1e-8]

terrain_tri=object_triangles(terrain_obj)
tri_lo=terrain_tri[:,:,:2].min(1);tri_hi=terrain_tri[:,:,:2].max(1)
def plane_height(tri,coords):
    a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;d=coords-a
    det=u[0]*v[1]-u[1]*v[0]
    s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det
    return tri[0,2]+s*(tri[1,2]-tri[0,2])+t*(tri[2,2]-tri[0,2])

def terrain_extents(poly):
    xmin,ymin,xmax,ymax=poly.bounds
    ids=np.where((tri_hi[:,0]>=xmin)&(tri_lo[:,0]<=xmax)&(tri_hi[:,1]>=ymin)&(tri_lo[:,1]<=ymax))[0]
    values=[]
    for i in ids:
        cut=Polygon(terrain_tri[i,:,:2]).intersection(poly)
        coords=shapely.get_coordinates(cut)
        if len(coords):values.extend(plane_height(terrain_tri[i],coords).tolist())
    if not values:raise ValueError('No terrain under pad')
    return min(values),max(values)

class LocalHeightField:
    def __init__(self,objs,bounds):
        self.tri=np.concatenate([object_triangles(o,bounds) for o in objs])
        xy=self.tri[:,:,:2].reshape(-1,2)
        unique,indices=np.unique(xy,axis=0,return_inverse=True)
        self.tree=BVHTree.FromPolygons(np.c_[unique,np.zeros(len(unique))].tolist(),indices.reshape(-1,3).tolist(),all_triangles=True)
    def height(self,xy):
        p=np.asarray(xy[:2],np.float64);vals=[]
        for _,_,i,_ in self.tree.find_nearest_range(Vector((float(p[0]),float(p[1]),0)),.002):
            tri=self.tri[i];a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;d=p-a
            det=u[0]*v[1]-u[1]*v[0];s=(d[0]*v[1]-d[1]*v[0])/det;t=(u[0]*d[1]-u[1]*d[0])/det
            if min(1-s-t,s,t)>=-1e-7:vals.append((1-s-t)*tri[0,2]+s*tri[1,2]+t*tri[2,2])
        return None if not vals else float(max(vals))

def empty(name,parent):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=parent;return o
def mesh(name,vertices,faces,material,parent,uvs=None):
    d=bpy.data.meshes.new(name);d.from_pydata(vertices,[],faces);d.materials.append(material);d.update()
    o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.parent=parent
    if uvs is not None:
        layer=d.uv_layers.new(name='UVMap')
        indices=np.empty(len(d.loops),np.int32);d.loops.foreach_get('vertex_index',indices)
        layer.data.foreach_set('uv',np.asarray(uvs,np.float32)[indices].ravel())
    return o
def new_material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.9
    return m

# The existing terrain already excludes road and sidewalk footprints. Duplicate
# only the CBD portions, preserving its height plane and clipping small parks.
cbd=Polygon(data['cbd_boundary'])
parks=[Polygon(p) for p in data['green_pockets']]
mask=cbd.difference(unary_union(parks))
xmin,ymin,xmax,ymax=cbd.bounds
sel=(tri_hi[:,0]>=xmin)&(tri_lo[:,0]<=xmax)&(tri_hi[:,1]>=ymin)&(tri_lo[:,1]<=ymax)
local=terrain_tri[sel]
polys=shapely.polygons(local[:,:,:2])
inside=shapely.covers(mask,polys)
raw=local[inside].copy()
pieces=[raw]
partial=np.flatnonzero(~inside & shapely.intersects(mask,polys))
extras=[];covered_area=float(np.sum(shapely.area(polys[inside])))
for i in partial:
    cut=shapely.intersection(mask,polys[i])
    covered_area+=float(shapely.area(cut))
    if cut.is_empty or cut.area<1e-9:continue
    for part in shapely.get_parts(shapely.constrained_delaunay_triangles(cut)):
        if part.is_empty or part.area<1e-9:continue
        xy=np.asarray(part.exterior.coords)[:3,:2]
        zz=plane_height(local[i],xy)
        tri=np.c_[xy,zz]
        det=np.cross(tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2])
        if det<0:tri=tri[::-1]
        extras.append(tri)
if extras:pieces.append(np.asarray(extras))
paved=np.concatenate(pieces);paved[:,:,2]+=.012
vertices=paved.reshape(-1,3);faces=np.arange(len(vertices),dtype=np.int32).reshape(-1,3)
pav_group=empty('10_CBD_HARDSCAPE',root)
paver_mat=new_material('CBD_Concrete_Paver_Tiles',(.52,.51,.49))
im=bpy.data.images.load(str(args.pavers.resolve()),check_existing=True);im.pack()
nodes=paver_mat.node_tree.nodes;image=nodes.new('ShaderNodeTexImage');image.image=im;image.extension='REPEAT'
paver_mat.node_tree.links.new(image.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
paver=mesh('CBD_Conforming_Concrete_Paving',vertices.tolist(),faces.tolist(),paver_mat,pav_group,vertices[:,:2]/8)
paver['purpose']='Terrain-conforming concrete paving with retained landscaped pockets'
paver['surface_offset_m']=.012;paver['paved_area_m2']=covered_area
print('CBD_PAVING',json.dumps({'area_m2':covered_area,'triangles':len(paved),'green_pockets':len(parks)}),flush=True)
del paved,vertices,faces,pieces,extras,polys,local;gc.collect()

# Fill vacant CBD parcels with replaceable simple massing. Bases penetrate the
# local surface slightly so no corner is suspended above uneven ground.
cube_mesh=bpy.data.meshes.new('CBD_Infill_Shared_Unit_Box')
cube_mesh.from_pydata([(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)],[],
                      [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
cube_mesh.materials.append(bpy.data.objects['MAIN_CBD_0123'].data.materials[0]);cube_mesh.update()
main_group=bpy.data.objects['MAIN_CBD_0123'].parent
infill=[];rejected=[]
for item in data['cbd_infill_candidates']:
    footprint=Polygon(item['footprint']);x,y=item['center'];w,d,h=item['size']
    coords=np.array([[x+u*w/2,y+v*d/2] for u in np.linspace(-1,1,5) for v in np.linspace(-1,1,5)])
    values=[terrain.height(q) for q in coords]
    if any(z is None for z in values):rejected.append([item['name'],'terrain opening']);continue
    zmin,zmax=terrain_extents(footprint)
    if zmax-zmin>4:rejected.append([item['name'],'excessive slope']);continue
    base=zmin-.15
    o=bpy.data.objects.new(item['name'],cube_mesh);sc.collection.objects.link(o);o.parent=main_group
    o.location=(x,y,base+h/2);o.scale=(w,d,h)
    o['is_placeholder']=True;o['district']='CBD';o['replaceable_id']=item['name'];o['terrain_range_m']=zmax-zmin
    item['base']=base;item['terrain_min_m']=zmin;item['terrain_max_m']=zmax
    infill.append(item)
plan['buildings'].extend(infill)
print('CBD_INFILL',json.dumps({'added':len(infill),'rejected':rejected}),flush=True)

# Preflight two separate apartment lots against the actual sidewalk and terrain.
sidewalk_objects=[bpy.data.objects['MAIN_Sidewalk_Modular_Continuous'],bpy.data.objects['Sidewalk_Continuous_Transition_Base']]
def preflight(site,walk):
    polygon=Polygon(site['pad_xy'])
    zmin,zmax=terrain_extents(polygon)
    corners=np.asarray(site['pad_xy']);u=corners[1]-corners[0];v=corners[3]-corners[0]
    for aa in np.linspace(0,1,21):
        for bb in np.linspace(0,1,15):
            z=terrain.height(corners[0]+aa*u+bb*v)
            if z is None:raise ValueError('pad crosses a terrain opening')
            zmin=min(zmin,z);zmax=max(zmax,z)
    if zmax-zmin>4:raise ValueError('pad is on an excessively steep site')
    top=zmax+.08
    start=np.asarray(site['access_start_xy']);end=np.asarray(site['access_end_xy'])
    length=float(np.linalg.norm(end-start));direction=(end-start)/length;across=np.array([-direction[1],direction[0]])
    offsets=np.linspace(-1.5,1.5,7);endxy=end[None,:]+offsets[:,None]*across
    walk_z=np.array([walk.height(q) if walk.height(q) is not None else np.nan for q in endxy])
    if not np.isfinite(walk_z).all():raise ValueError('access endpoint does not meet sidewalk')
    endcenter=float(walk_z.mean());crossfall=walk_z-endcenter
    stations=np.unique(np.r_[np.linspace(0,length,int(math.ceil(length/.75))+1),np.arange(16.9048,length,16.9048)])
    xy=start[None,None,:]+stations[:,None,None]/length*(end-start)[None,None,:]+offsets[None,:,None]*across[None,None,:]
    ground=np.array([[terrain.height(q) if terrain.height(q) is not None else np.nan for q in row] for row in xy])
    fraction=stations/length;roll=fraction[:,None]*crossfall[None,:]
    hh=(top+.004)*(1-fraction)+(endcenter+.006)*fraction
    required=np.max(np.where(np.isfinite(ground),ground-roll+.025,-1e6),axis=1);hh=np.maximum(hh,required)
    for k in range(1,len(hh)):hh[k]=max(hh[k],hh[k-1]-.05*(stations[k]-stations[k-1]))
    for k in range(len(hh)-2,-1,-1):hh[k]=max(hh[k],hh[k+1]-.05*(stations[k+1]-stations[k]))
    if abs(hh[0]-top-.004)>.012 or abs(hh[-1]-endcenter-.006)>.012:raise ValueError('access grade cannot meet both ends')
    zz=hh[:,None]+roll
    return {'terrain_min':zmin,'terrain_max':zmax,'top':top,'bottom':zmin-.2,'stations':stations,'xy':xy,'z':zz,
            'ground':ground,'walk_z':walk_z,'length':length,'endxy':endxy}

chosen=None;attempts=[]
for pair in data['oldtown_candidate_pairs']:
    sites=pair['instances'];points=np.array([s['center'] for s in sites]+[s['road_nearest'] for s in sites])
    lo=points.min(0)-50;hi=points.max(0)+50
    try:
        walk=LocalHeightField(sidewalk_objects,[lo[0],lo[1],hi[0],hi[1]])
        evaluated=[preflight(site,walk) for site in sites]
        chosen=(sites,evaluated);break
    except (ValueError,IndexError) as err:
        attempts.append({'placeholders':[s['placeholder'] for s in sites],'reason':str(err)})
        print('REJECT_LOTS',attempts[-1],flush=True)
    finally:
        del walk;gc.collect()
if chosen is None:raise RuntimeError('No candidate pair passed exact terrain and sidewalk checks: '+str(attempts))
sites,prepared=chosen
apt_group=empty('09_OLDTOWN_REAL_BUILDINGS',root)
site_group=empty('11_OLDTOWN_SITE_ADAPTATION',root)
foundation_mat=new_material('Oldtown_Level_Foundation_Concrete',(.37,.36,.33))
walkmat=bpy.data.materials['Road_Modular_Original_Atlas']
source_files={'apartment_2':args.apartment_2,'apartment_3':args.apartment_3}
removed=[];records=[]
for site,prep in zip(sites,prepared):
    src=source_files[site['model']];name='OLDTOWN_Apartment_0'+site['model'][-1]
    old=bpy.data.objects.get(site['placeholder']);assert old and old.get('is_placeholder')
    prior=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(src.resolve()));bpy.context.view_layer.update()
    imported=set(sc.objects)-prior;source_meshes=[o for o in imported if o.type=='MESH'];assert len(source_meshes)==1
    points=np.vstack([np.array([o.matrix_world@v.co for v in o.data.vertices]) for o in source_meshes])
    lo=points.min(0);hi=points.max(0);dims=hi-lo;scale=site['target_height_m']/dims[2];size=dims*scale
    assert np.max(np.abs(size-np.array(site['approx_source_size_m'])))<.01
    center=np.array(site['center']);angle=site['angle'];body=prep['top']-.025
    instance=empty(name,apt_group)
    instance.matrix_world=Matrix.Translation((center[0],center[1],body))@Matrix.Rotation(angle,4,'Z')@Matrix.Scale(scale,4)@Matrix.Translation((-float((lo[0]+hi[0])/2),-float((lo[1]+hi[1])/2),-float(lo[2])))
    for obj in imported:
        if obj.parent not in imported:
            original=obj.matrix_world.copy();obj.parent=instance;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=original
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    instance['is_building_instance']=True;instance['is_placeholder']=False;instance['source_filename']=src.name;instance['source_sha256']=digest
    instance['district']='OLDTOWN';instance['region']='MAIN';instance['target_height_m']=site['target_height_m']
    instance['uniform_scale']=scale;instance['replaces_placeholder']=site['placeholder']
    for i,obj in enumerate(source_meshes):obj.name=name+'_Source_Mesh_%02d'%i;obj['source_filename']=src.name;obj['is_placeholder']=False
    rect=np.asarray(site['pad_xy']);top=prep['top'];bottom=prep['bottom']
    verts=[[float(x),float(y),top] for x,y in rect]+[[float(x),float(y),bottom] for x,y in rect]
    # All site polygons have positive orientation from the planner.
    faces=[[0,1,2,3],[7,6,5,4]]+[[i,(i+1)%4,(i+1)%4+4,i+4] for i in range(4)]
    pad=mesh(name+'_Level_Foundation',verts,faces,foundation_mat,site_group)
    pad['purpose']='Level concrete base; original model apron is embedded by 25 mm'
    xy=prep['xy'];zz=prep['z'];stations=prep['stations'];nv=zz.size;cols=zz.shape[1]
    finite=prep['ground'][np.isfinite(prep['ground'])];floor=float(finite.min())-.20
    v=np.dstack([xy,zz]).reshape(-1,3).tolist()+np.dstack([xy,np.full_like(zz,floor)]).reshape(-1,3).tolist()
    faces=[];uvfaces=[]
    for row in range(len(stations)-1):
        tile=math.floor(((stations[row]+stations[row+1])/2)/16.9048)
        for col in range(cols-1):
            a=row*cols+col;b=(row+1)*cols+col
            for face in [[a,b,b+1],[a,b+1,a+1]]:
                faces.append(face);uvfaces.append([(.271-.055*(i%cols)/(cols-1),.7766-.1777*(stations[i//cols]-tile*16.9048)/16.9048) for i in face])
                faces.append([i+nv for i in face[::-1]]);uvfaces.append([(.216,.67)]*3)
    ring=list(range(cols))+[r*cols+cols-1 for r in range(1,len(stations))]+list(range(nv-2,nv-cols-1,-1))+[r*cols for r in range(len(stations)-2,0,-1)]
    for a,b in zip(ring,ring[1:]+ring[:1]):faces.append([a,b,b+nv,a+nv]);uvfaces.append([(.216,.67),(.216,.69),(.216,.69),(.216,.67)])
    ramp=mesh(name+'_Sidewalk_Access',v,faces,walkmat,site_group)
    layer=ramp.data.uv_layers.new(name='UVMap')
    for poly,uv in zip(ramp.data.polygons,uvfaces):
        for li,coord in zip(poly.loop_indices,uv):layer.data[li].uv=coord
    grade=float(np.max(np.abs(np.diff(zz,axis=0))/np.diff(stations)[:,None]))
    ramp['walkable']=True;ramp['source_material']='Road Modular original sidewalk atlas';ramp['maximum_longitudinal_grade']=grade
    record=dict(site);record.update(instance_name=name,source_filename=src.name,source_sha256=digest,uniform_scale=float(scale),
        source_dimensions_m=dims.tolist(),placed_dimensions_m=size.tolist(),source_mesh_count=len(source_meshes),
        foundation_top_m=top,foundation_bottom_m=bottom,building_base_m=body,terrain_min_m=prep['terrain_min'],
        terrain_max_m=prep['terrain_max'],footprint_xy=rect.tolist(),access_length_m=prep['length'],access_width_m=3.,
        access_maximum_grade=grade,access_end_lip_m=float(np.max(np.abs(zz[-1]-prep['walk_z']))),
        access_end_samples_xyz=np.c_[prep['endxy'],zz[-1]].tolist())
    records.append(record);removed.append(old.name);bpy.data.objects.remove(old,do_unlink=True)
    print('OLDTOWN_PLACED',json.dumps(record),flush=True)
plan['buildings']=[b for b in plan['buildings'] if b['name'] not in removed]
plan['real_buildings'].extend(records)
plan['stats']['placeholder_buildings']=len(plan['buildings']);plan['stats']['real_buildings']=len(plan['real_buildings'])
plan['stats']['buildings']=len(plan['buildings'])+len(plan['real_buildings'])
plan['stats']['cbd_infill_added']=len(infill);plan['stats']['cbd_hardscape_area_m2']=covered_area
root['description']='Three-island road city with denser paved CBD and four user-supplied buildings.'
root['placeholder_building_count']=len(plan['buildings']);root['real_building_count']=len(plan['real_buildings'])
bpy.context.view_layer.update();after=fingerprint(protected)
assert before==after,'Original road, sidewalk, or terrain geometry was modified'
report={'instances':records,'removed_placeholders':removed,'attempts_rejected':attempts,'cbd_added_placeholders':len(infill),
        'cbd_rejected_candidates':rejected,'cbd_paved_area_m2':covered_area,'green_pockets':len(parks),
        'original_geometry_sha256_before':before,'original_geometry_sha256_after':after,
        'original_road_sidewalk_terrain_unchanged':before==after,'placeholder_buildings':len(plan['buildings']),'building_total':plan['stats']['buildings']}
(args.out/'urban_update.json').write_text(json.dumps(report,indent=2))
(args.out/'city_plan.json').write_text(json.dumps(plan,separators=(',',':')))
for image in bpy.data.images:
    if image.type=='IMAGE' and image.size[0]>2 and not image.packed_file:
        try:image.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((args.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,
    export_animations=False,export_cameras=False,export_lights=False,export_materials='EXPORT',export_image_format='AUTO',
    export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. '+plan['sources']['road']['url']+' Four user-provided building assets.')
print('URBAN_UPDATE_COMPLETE',json.dumps({'glb_bytes':(args.out/'huizhou_road_network.glb').stat().st_size,
      'added_cbd_boxes':len(infill),'oldtown_assets':len(records),'placeholder_count':len(plan['buildings'])}),flush=True)
