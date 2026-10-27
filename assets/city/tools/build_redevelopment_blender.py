"""Add editable blockout streets, urban podiums and district features."""
from pathlib import Path
import argparse,gzip,json,math,random,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--old-parks',type=Path,required=True)
ap.add_argument('--shapely-path',type=Path);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.shapely_path:sys.path.insert(0,str(args.shapely_path.resolve()))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,nearest_points
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField

bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));bpy.context.view_layer.update()
sc=bpy.context.scene;plan=json.loads(args.plan.read_text());scheme=json.loads(args.scheme.read_text())
parks=json.loads(gzip.decompress(args.old_parks.read_bytes()))['green_pockets']
root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout'];rng=random.Random(1327028)
def group(name,parent=root):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=parent;return o
cbd_group=group('13_CBD_PODIUM_AND_PUBLIC_SPACE')
old_group=group('14_OLDTOWN_BLOCKOUT_AND_COURTYARDS')
port_group=group('15_PORT_AND_LOGISTICS_BLOCKOUT')
land_group=group('16_LAKESIDE_AND_PROMENADE')
civic_group=group('17_CIVIC_UNIVERSITY_CULTURE')
road_group=group('18_SIGNALS_AND_BRIDGE_GUIDANCE')
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.88
    return m
mats={
 'podium':material('CBD_Podium_Blockout',(.42,.46,.46)),
 'arcade':material('Oldtown_Arcade_Placeholder',(.55,.45,.35)),
 'housing':material('Oldtown_Housing_Placeholder',(.55,.50,.42)),
 'lake':material('Lakeside_Lowrise_Placeholder',(.60,.57,.49)),
 'civic':material('Civic_Public_Building_Placeholder',(.51,.54,.52)),
 'yard':material('Port_Yard_Concrete',(.36,.39,.38)),
 'crane':material('Port_Crane_Blockout',(.72,.40,.08)),
 'sign':material('Road_Sign_Blockout',(.12,.17,.18)),
 'pole':material('Road_Light_Pole_Blockout',(.45,.47,.46)),
 'tree':material('CBD_Small_Tree_Blockout',(.20,.32,.16)),
 'container_red':material('Container_Rust_Red',(.49,.17,.12)),
 'container_blue':material('Container_Deep_Blue',(.09,.26,.39)),
 'container_ochre':material('Container_Ochre',(.52,.36,.15)),
}
cubev=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
cubef=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
shared={}
def cube(name,center,size,mat,parent,angle=0,purpose='placeholder'):
    if mat.name not in shared:
        mesh=bpy.data.meshes.new('Shared_Blockout_'+mat.name);mesh.from_pydata(cubev,[],cubef);mesh.materials.append(mat);mesh.update();shared[mat.name]=mesh
    obj=bpy.data.objects.new(name,shared[mat.name]);sc.collection.objects.link(obj);obj.parent=parent
    obj.location=center;obj.scale=size;obj.rotation_euler[2]=angle;obj['is_placeholder']=True;obj['purpose']=purpose
    return obj
terrains={k:bpy.data.objects[k+'_Sculpted_Terrain'] for k in ['MAIN','WEST','EAST']}
fields={k:HeightField([o]) for k,o in terrains.items()}
def terrain_triangles(o):
    m=o.data;m.calc_loop_triangles()
    verts=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',verts);verts=verts.reshape(-1,3).astype(np.float64)
    trans=np.asarray(o.matrix_world,np.float64);verts=verts@trans[:3,:3].T+trans[:3,3]
    indices=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',indices);q=verts[indices.reshape(-1,3)]
    a=q[:,1,:2]-q[:,0,:2];b=q[:,2,:2]-q[:,0,:2];return q[(a[:,0]*b[:,1]-a[:,1]*b[:,0])>1e-8]
tris={k:terrain_triangles(o) for k,o in terrains.items()}
def sample_extents(region,polygon):
    pts=np.asarray(polygon.exterior.coords)[:4,:2];a=pts[0];u=pts[1]-a;v=pts[3]-a
    heights=[]
    for s in np.linspace(.001,.999,7):
        for t in np.linspace(.001,.999,7):
            z=fields[region].height(a+s*u+t*v)
            if z is None:return None
            heights.append(z)
    return min(heights),max(heights)
newroad=shapely.from_geojson(scheme['new_pavement']);newfull=shapely.from_geojson(scheme['new_full_footprint'])
report={'rejected':[],'cbd_podiums':[],'oldtown_arcade_blockouts':[],'oldtown_housing_blockouts':[],'west_lakeside_blockouts':[],
        'east_container_yards':[],'civic_public_buildings':[]}

park_polys=[Polygon(p) for p in parks]
small_parks=[]
for p in park_polys:
    c=p.centroid;small_parks.append(box(c.x-9,c.y-5,c.x+9,c.y+5))
for item in scheme['cbd_podiums']:
    poly=Polygon(item['footprint'])
    if any(poly.intersects(g) for g in small_parks):report['rejected'].append([item['name'],'retained tree planter']);continue
    heights=sample_extents('MAIN',poly)
    if heights is None or heights[1]-heights[0]>4:report['rejected'].append([item['name'],'terrain']);continue
    base=heights[0]-.18;x,y=item['center'];w,d,h=item['size']
    obj=cube(item['name'],(x,y,base+h/2),(w,d,h),mats['podium'],cbd_group,purpose='tower podium blockout')
    obj['parent_tower']=item['parent_tower'];item['base']=base;report['cbd_podiums'].append(item)

def add_buildings(items,region,zone,mat,parent,tag):
    for b in items:
        if tag=='west_lakeside_blockouts' and len(report[tag])>=8:break
        poly=Polygon(b['footprint']);heights=sample_extents(region,poly)
        if heights is None or heights[1]-heights[0]>4:report['rejected'].append([b['name'],'terrain']);continue
        base=heights[0]-.15;x,y=b['center'];w,d,h=b['size'];angle=b.get('angle',0)
        obj=cube(b['name'],(x,y,base+h/2),(w,d,h),mat,parent,angle,purpose=tag)
        obj['district']=zone;obj['replaceable_id']=b['name']
        item=dict(b);item.update(region=region,zone=zone,base=base)
        plan['buildings'].append(item);report[tag].append(item)
add_buildings(scheme['oldtown_arcade_blockouts'],'MAIN','OLDTOWN',mats['arcade'],old_group,'oldtown_arcade_blockouts')
add_buildings(scheme['oldtown_housing_blockouts'],'MAIN','OLDTOWN',mats['housing'],old_group,'oldtown_housing_blockouts')
add_buildings(scheme['west_lakeside_blockouts'],'WEST','RESORT',mats['lake'],land_group,'west_lakeside_blockouts')

# Place one recognizable public mass in each non-CBD district, as a replaceable
# block rather than a detailed building asset.
occupied=unary_union([newfull.buffer(3)]+[Polygon(b['footprint']).buffer(3) for b in plan['buildings']]
  +[Polygon(b['footprint_xy']).buffer(3) for b in plan['real_buildings']]
  +[LineString([b['access_start_xy'],b['access_end_xy']]).buffer(2) for b in plan['real_buildings']]
  +[Polygon(b['footprint']).buffer(2) for b in report['cbd_podiums']])
maincoast=Polygon(plan['coasts']['MAIN'])
for label,zone,target,w,d,h in [
    ('UNIVERSITY_Teaching_Blockout','UNIVERSITY',(-848,1037),44,25,18),
    ('CIVIC_City_Hall_Blockout','CIVIC',(1108,858),42,30,23),
    ('CULTURE_Public_Hall_Blockout','CULTURE',(1262,390),48,34,19),
]:
    found=None
    for _ in range(2000):
        x=target[0]+rng.uniform(-150,150);y=target[1]+rng.uniform(-150,150)
        poly=box(x-w/2,y-d/2,x+w/2,y+d/2)
        if not maincoast.buffer(-15).covers(poly) or poly.intersects(occupied):continue
        ht=sample_extents('MAIN',poly)
        if ht is None or ht[1]-ht[0]>4:continue
        found=(x,y,poly,ht);break
    if found is None:report['rejected'].append([label,'no unobstructed plot']);continue
    x,y,poly,ht=found;base=ht[0]-.15
    obj=cube(label,(x,y,base+h/2),(w,d,h),mats['civic'],civic_group,purpose='civic building blockout')
    obj['district']=zone;obj['replaceable_id']=label
    rec={'name':label,'center':[x,y],'size':[w,d,h],'footprint':[list(q) for q in poly.exterior.coords],
         'region':'MAIN','zone':zone,'base':base}
    plan['buildings'].append(rec);report['civic_public_buildings'].append(rec)
    occupied=unary_union([occupied,poly.buffer(3)])

def plane_z(tri,xy):
    a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;d=xy-a;det=u[0]*v[1]-u[1]*v[0]
    s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det
    return tri[0,2]+s*(tri[1,2]-tri[0,2])+t*(tri[2,2]-tri[0,2])
def overlay_terrain(name,region,mask,mat,parent,atlas=False):
    if mask.is_empty:return None,0
    q=tris[region];lo=q[:,:,:2].min(1);hi=q[:,:,:2].max(1);xmin,ymin,xmax,ymax=mask.bounds
    select=(hi[:,0]>=xmin)&(lo[:,0]<=xmax)&(hi[:,1]>=ymin)&(lo[:,1]<=ymax);q=q[select]
    ps=shapely.polygons(q[:,:,:2]);inside=shapely.covers(mask,ps);pieces=[q[inside].copy()];extras=[];area=float(np.sum(shapely.area(ps[inside])))
    for i in np.flatnonzero(~inside&shapely.intersects(mask,ps)):
        cut=shapely.intersection(ps[i],mask);area+=float(cut.area)
        if cut.is_empty or cut.area<1e-9:continue
        for poly in shapely.get_parts(shapely.constrained_delaunay_triangles(cut)):
            if poly.is_empty or poly.area<1e-9:continue
            xy=np.asarray(poly.exterior.coords)[:3,:2];z=plane_z(q[i],xy);t=np.c_[xy,z]
            cross=np.cross(t[1,:2]-t[0,:2],t[2,:2]-t[0,:2])
            if cross<0:t=t[::-1]
            extras.append(t)
    if extras:pieces.append(np.asarray(extras))
    if not any(len(piece) for piece in pieces):return None,0
    alltri=np.concatenate(pieces);alltri[:,:,2]+=.014
    vertices=alltri.reshape(-1,3);faces=np.arange(len(vertices)).reshape(-1,3)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices.tolist(),[],faces.tolist());mesh.materials.append(mat);mesh.update()
    obj=bpy.data.objects.new(name,mesh);sc.collection.objects.link(obj);obj.parent=parent
    uv=mesh.uv_layers.new(name='UVMap')
    if atlas:
        u=.216+.055*np.mod(vertices[:,0]/5,1);v=.599+.1777*np.mod(vertices[:,1]/16.9048,1)
        coords=np.c_[u,v]
    else:coords=vertices[:,:2]/8
    uv.data.foreach_set('uv',coords.astype(np.float32).ravel());return obj,area

paver=bpy.data.materials['CBD_Concrete_Paver_Tiles'];sidewalk=bpy.data.materials['Road_Modular_Original_Atlas.001']
parks_fill=unary_union(park_polys).difference(unary_union(small_parks)).difference(newfull)
_,reclaimed=overlay_terrain('CBD_Rectangular_Planter_Reclaimed_Paving','MAIN',parks_fill,paver,cbd_group)
for i,poly in enumerate(small_parks):
    c=poly.centroid;z=fields['MAIN'].height((c.x,c.y))
    if z is None:continue
    # Small cubic trees remain replaceable blockout objects.
    cube('CBD_Tree_Trunk_%02d'%i,(c.x,c.y,z+1.25),(.55,.55,2.5),mats['housing'],cbd_group,purpose='tree placeholder')
    cube('CBD_Tree_Canopy_%02d'%i,(c.x,c.y,z+4.0),(3.2,3.2,3.0),mats['tree'],cbd_group,purpose='tree placeholder')
report['cbd_green_pockets']=len(small_parks);report['cbd_reclaimed_paving_m2']=reclaimed

# A shared neighbourhood courtyard links the two existing apartment aprons.
real=[b for b in plan['real_buildings'] if b['instance_name'].startswith('OLDTOWN_Apartment')]
if len(real)==2:
    p0=np.asarray(real[0]['footprint_xy']);p1=np.asarray(real[1]['footprint_xy'])
    # Pick the eastern edge of the western lot and western edge of the eastern lot.
    west,east=sorted(real,key=lambda r:r['center'][0]);pa=Polygon(west['footprint_xy']);pb=Polygon(east['footprint_xy'])
    a,b=nearest_points(pa,pb);start=np.array(a.coords[0]);end=np.array(b.coords[0]);unit=(end-start)/np.linalg.norm(end-start)
    start-=unit*.4;end+=unit*.4;normal=np.array([-unit[1],unit[0]])
    z0=west['foundation_top_m']+.004;z1=east['foundation_top_m']+.004
    n=max(3,int(math.ceil(np.linalg.norm(end-start)/1.0))+1);stations=np.linspace(0,1,n);positions=start[None,:]+stations[:,None]*(end-start)
    vv=[]
    for s,xy in zip(stations,positions):
        for side in [-1,1]:vv.append([*(xy+normal*side*1.3),z0*(1-s)+z1*s])
    ff=[]
    for i in range(n-1):ff.extend([[2*i,2*i+2,2*i+3],[2*i,2*i+3,2*i+1]])
    mesh=bpy.data.meshes.new('Oldtown_Apartment_Courtyard_Walk');mesh.from_pydata(vv,[],ff);mesh.materials.append(sidewalk);mesh.update()
    obj=bpy.data.objects.new('Oldtown_Apartment_Courtyard_Walk',mesh);sc.collection.objects.link(obj);obj.parent=old_group;obj['walkable']=True
    uv=mesh.uv_layers.new(name='UVMap');ids=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',ids)
    xyz=np.asarray(vv);coords=np.c_[.216+.055*np.mod(xyz[:,0]/5,1),.599+.1777*np.mod(xyz[:,1]/16.9048,1)]
    uv.data.foreach_set('uv',coords[ids].astype(np.float32).ravel())
    court=LineString([start,end]).buffer(6,cap_style='flat').difference(newfull).difference(pa.union(pb))
    _,court_area=overlay_terrain('Oldtown_Residential_Courtyard_Paving','MAIN',court,paver,old_group)
    report['oldtown_courtyard']={'length_m':float(np.linalg.norm(end-start)),'width_m':2.6,'paved_area_m2':court_area}

# Main-island south shore promenade: land-conforming and clipped away from the
# carriageway. The original sidewalks stay present where routes meet.
coast=Polygon(plan['coasts']['MAIN'])
shore=coast.buffer(-28).boundary.intersection(box(-2000,-250,2000,370))
shore_buildings=unary_union([Polygon(b['footprint']).buffer(1) for b in plan['buildings']]
  +[Polygon(b['footprint_xy']).buffer(1) for b in plan['real_buildings']])
promenade=shore.buffer(2.5,cap_style='flat').difference(newroad).difference(shore_buildings)
_,prom_area=overlay_terrain('Main_Southern_Waterfront_Walk','MAIN',promenade,sidewalk,land_group,True)
report['waterfront_promenade_area_m2']=prom_area

# Low concrete yards with organized container stacks.
for yard in scheme['east_container_yards']:
    poly=Polygon(yard['footprint']);ht=sample_extents('EAST',poly)
    if ht is None or ht[1]-ht[0]>5:report['rejected'].append([yard['name'],'terrain']);continue
    x,y=yard['center'];w,d=yard['size'];top=ht[1]+.08;bottom=ht[0]-.25
    pad=cube(yard['name']+'_Level_Concrete',(x,y,(top+bottom)/2),(w,d,top-bottom),mats['yard'],port_group,purpose='port yard')
    pad['foundation_bottom_m']=bottom;pad['foundation_top_m']=top
    count=0
    xs=np.arange(-w/2+8,w/2-7,16);ys=np.r_[np.arange(-d/2+4,-3,4.5),np.arange(6,d/2-2,4.5)]
    for i,xx in enumerate(xs):
        for j,yy in enumerate(ys):
            for k in range(2 if (i+j)%3 else 3):
                mat=mats[['container_red','container_blue','container_ochre'][(i+j+k)%3]]
                cube(yard['name']+'_Container_%03d'%count,(x+xx,y+yy,top+1.3+2.6*k),(12,2.4,2.6),mat,port_group,purpose='container blockout');count+=1
    rec=dict(yard);rec.update(foundation_top_m=top,foundation_bottom_m=bottom,container_count=count,terrain_relief_m=ht[1]-ht[0])
    report['east_container_yards'].append(rec)
for i,p in enumerate(plan['props']):
    if p['zone']!='DOCK':continue
    x,y=p['center'];deck=p['base']+p['size'][2];height=23
    for xx in [-10,10]:
        for yy in [-8,8]:
            cube('PORT_Quay_Crane_%02d_Leg_%s_%s'%(i,xx,yy),(x+xx,y+yy,deck+height/2),(1.8,1.8,height),mats['crane'],port_group,purpose='gantry crane blockout')
    cube('PORT_Quay_Crane_%02d_Crossbeam'%i,(x,y,deck+height),(24,2.2,2.0),mats['crane'],port_group,purpose='gantry crane blockout')
    cube('PORT_Quay_Crane_%02d_Boom'%i,(x,y+16,deck+height+1.2),(3,43,2),mats['crane'],port_group,purpose='gantry crane blockout')
report['port_cranes']=len([p for p in plan['props'] if p['zone']=='DOCK'])

# Signal poles at sidewalk outside edges near four rebuilt intersections.
newwalk=newfull.difference(newroad)
lights=0
for entry in scheme['repairs']:
    center=np.asarray(entry['node_xy'])
    for deg in [45,135,225,315]:
        v=np.array([math.cos(math.radians(deg)),math.sin(math.radians(deg))]);candidate=None
        for r in np.arange(10,32,.5):
            xy=center+v*r;point=Point(xy)
            if newwalk.covers(point) and newroad.distance(point)>2.35:
                candidate=xy;break
        if candidate is None:continue
        z=fields['MAIN'].height(candidate)
        if z is None:
            # The sidewalk replaces the terrain; use the junction height.
            z=entry['target_height_m']+.14
        cube('Junction_Signal_Pole_%03d'%lights,(candidate[0],candidate[1],z+1.8),(.18,.18,3.6),mats['pole'],road_group,purpose='signal pole blockout')
        cube('Junction_Signal_Box_%03d'%lights,(candidate[0],candidate[1],z+3.55),(.55,.4,.95),mats['sign'],road_group,purpose='traffic signal blockout')
        lights+=1
report['signal_poles']=lights

# Bridge guidance is deliberately limited to the water junction's existing
# deck edge, leaving the carriageway and both original sidewalks unobstructed.
bnode=min(plan['nodes'],key=lambda n:(n['xy'][0]-178.0742)**2+(n['xy'][1]+876.2769)**2)
bx,by=bnode['xy'];bz=bnode['z']
bridge_signs=0
for side in [-1,1]:
    point=None
    for rr in np.arange(14,42,.5):
        for deg in ([225,200,250] if side<0 else [315,340,290]):
            xy=np.array([bx+rr*math.cos(math.radians(deg)),by+rr*math.sin(math.radians(deg))])
            candidate=Point(xy)
            if newwalk.covers(candidate) and newroad.distance(candidate)>2.35:point=xy;break
        if point is not None:break
    if point is None:continue
    cube('Bridge_Approach_Sign_Post_%s'%side,(point[0],point[1],bz+2),(.22,.22,4),mats['pole'],road_group,purpose='bridge sign post')
    cube('Bridge_Approach_Sign_%s'%side,(point[0],point[1],bz+4.1),(2.5,.25,1.2),mats['sign'],road_group,purpose='bridge direction sign')
    bridge_signs+=1
report['bridge_guidance_signs']=bridge_signs

stats=plan['stats'];stats['placeholder_buildings']=len(plan['buildings']);stats['real_buildings']=len(plan['real_buildings'])
stats['buildings']=len(plan['buildings'])+len(plan['real_buildings'])
stats['redevelopment_podiums']=len(report['cbd_podiums']);stats['new_oldtown_blockouts']=len(report['oldtown_arcade_blockouts'])+len(report['oldtown_housing_blockouts'])
root['placeholder_building_count']=stats['placeholder_buildings'];root['real_building_count']=stats['real_buildings']
root['description']='Three-island road city, locally repaired junctions and editable urban district blockouts.'
plan['redevelopment_podiums']=report['cbd_podiums'];plan['redevelopment_features']={'east_container_yards':report['east_container_yards'],'waterfront_promenade_area_m2':prom_area}
args.out.mkdir(parents=True,exist_ok=True);(args.out/'city_plan.json').write_text(json.dumps(plan,separators=(',',':')))
(args.out/'district_redevelopment.json').write_text(json.dumps(report,indent=2))
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'redeveloped.blend').resolve()),compress=True)
print('DISTRICT_REDEVELOPMENT_COMPLETE',json.dumps({'podiums':len(report['cbd_podiums']),
 'arcades':len(report['oldtown_arcade_blockouts']),'housing':len(report['oldtown_housing_blockouts']),
 'yards':len(report['east_container_yards']),'lake':len(report['west_lakeside_blockouts']),
 'civic':len(report['civic_public_buildings']),'signals':lights,'promenade_m2':prom_area,'rejected':report['rejected']}),flush=True)
