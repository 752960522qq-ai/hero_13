"""Build the reconstructed city at native metre scale, with original texture bytes."""
import argparse,json,sys,math,hashlib,collections
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
ap=argparse.ArgumentParser()
for k in ['plan','meshes','roads','models','deps','out']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).parent))
from compact_city_math import *
from shapely.geometry import box
from shapely import affinity
a.out.mkdir(parents=True,exist_ok=True);p=json.loads(a.plan.read_text());sc=bpy.context.scene
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(a.roads.resolve()));bpy.context.view_layer.update();roadmat=next(o.data.materials[0] for o in sc.objects if o.type=='MESH' and any('Road_33_69' in q.name for q in [o,*o.parent_recursive])) if False else None
for o in sc.objects:
    if o.type!='MESH':continue
    q=o
    while q:
        if 'Road_33_69' in q.name:roadmat=o.data.materials[0];break
        q=q.parent
    if roadmat:break
assert roadmat;roadmat.name='Road_Modular_Original_Atlas';roadmat.use_fake_user=True
for o in list(sc.objects):bpy.data.objects.remove(o,do_unlink=True)
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=parent;return o
root=empty('Huizhou_Reconstructed_City_3p25km2');root['units']='metres';root['net_land_area_m2']=p['stats']['land_area_m2'];root['global_scale_applied']=False;root['version']='v10_reconstruction_640_buildings';root['description']='New coast geometry and layered street graph; existing asset metric heights retained.'
groups={s:empty(s,root) for s in ['01_TERRAIN','02_WATER','03_ROAD_NETWORK','04_BRIDGE_STRUCTURES','05_BUILDING_PLACEHOLDERS','06_SIDEWALKS','07_SOURCE_BUILDINGS','08_BUILDING_FOOTINGS','09_CITY_INTERCHANGES','10_PEDESTRIAN_NETWORK','11_PORT_AND_PUBLIC_SPACES']}
def material(name,color,rough=.87,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
concrete=material('Bridge_Concrete',(.36,.38,.36));roof=material('Placeholder_Roofs',(.40,.39,.34));seam=material('Oldtown_Seam_Plaster',(.53,.48,.38));water=material('Sea',(.032,.18,.24),.32,.06);lake_mat=material('Lake',(.065,.25,.23),.44)
asphalt=material('Continuous_Junction_Asphalt',(.07,.075,.076),.95)
pal={'OLDTOWN':(.64,.55,.42),'CBD':(.51,.65,.69),'RESIDENTIAL':(.66,.64,.57),'CIVIC':(.72,.70,.62),'UNIVERSITY':(.63,.56,.44),'VILLAGE':(.65,.56,.44),'INDUSTRIAL':(.48,.58,.60)}
buildmats={k:material('Placeholder_'+k,c) for k,c in pal.items()};paint=material('Crosswalk_Paint',(.82,.82,.74));railmat=material('Concrete_Parapets',(.66,.67,.61))
def mesh(name,v,f,mats,parent,uv=None,mi=None,lot=None):
    v=np.asarray(v,np.float32);f=np.asarray(f,np.int32);me=bpy.data.meshes.new(name);me.vertices.add(len(v));me.vertices.foreach_set('co',v.ravel());me.loops.add(f.size);me.loops.foreach_set('vertex_index',f.ravel());me.polygons.add(len(f));me.polygons.foreach_set('loop_start',np.arange(len(f),dtype=np.int32)*f.shape[1]);me.polygons.foreach_set('loop_total',np.full(len(f),f.shape[1],np.int32))
    for m in mats:me.materials.append(m)
    if uv is not None:me.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uv,np.float32)[f].ravel())
    if mi is not None:me.polygons.foreach_set('material_index',np.asarray(mi,np.int32))
    if lot is not None:me.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',np.asarray(lot,np.int32))
    me.update();o=bpy.data.objects.new(name,me);sc.collection.objects.link(o);o.parent=parent;return o
def cellmesh(name,v,f,mats,parent,uv=None,kind=None,layer=None,color=None):
    v=np.asarray(v);f=np.asarray(f);centers=v[f].mean(1);keys=np.floor(centers[:,:2]/250).astype(int);unique,ids=np.unique(keys,axis=0,return_inverse=True)
    for j,key in enumerate(unique):
        take=np.flatnonzero(ids==j);ff=f[take];used,inverse=np.unique(ff.ravel(),return_inverse=True);o=mesh(name+'_Cell_%d_%d'%tuple(key),v[used],inverse.reshape(ff.shape),mats,parent,np.asarray(uv)[used] if uv is not None else None)
        if kind:o['surface_type']=kind
        if layer:o['surface_group']=layer
        if color is not None:
            cc=np.asarray(color)[used];o.data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',cc.astype(np.float32).ravel())
    return len(unique)
for info in json.loads((a.meshes/'surface_groups.json').read_text()):
    q=np.load(a.meshes/info['file']);kind=info['kind'];parent=groups['06_SIDEWALKS'] if kind in ['sidewalk','curb'] else groups['03_ROAD_NETWORK'];cellmesh(info['layer']+'_'+kind,q['vertices'],q['faces'],[asphalt if kind=='pavement' else roadmat],parent,q['uv'],kind,info['layer'])
print('ROAD_NETWORK_BUILT',flush=True)
islands={k:Polygon(v) for k,v in p['coasts'].items()};lake=Polygon(p['lake']);ground=[e for e in p['edges'] if e['layer'].startswith('GROUND')]
for e in p['edges']:
    if e['layer'].endswith('UPPER'):
        co=np.asarray(e['points']);delta=co[:,2]-raw_height(co[:,:2],islands,lake)
        if abs(delta).max()<2:ground.append(e)
gp=SurfaceProjector(ground)
def groundz(xy):return terrain_height(xy,islands,lake,gp)
terrainmat=material('Sculpted_City_Ground',(.50,.54,.37));nt=terrainmat.node_tree;bs=nt.nodes['Principled BSDF'];vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='Color';nt.links.new(vc.outputs['Color'],bs.inputs['Base Color'])
for reg in islands:
    q=np.load(a.meshes/f'terrain_{reg}.npz');co=q['vertices'];colors=np.tile([.36,.43,.29,1],(len(co),1))
    if reg=='MAIN':
        old=(co[:,1]>60)&(co[:,1]<480)&(co[:,0]>-420)&(co[:,0]<470);colors[old]=[.52,.48,.38,1];urban=(co[:,1]>620)&(co[:,1]<1340);colors[urban]=[.48,.50,.44,1]
    elif reg=='EAST':colors[:]=[.46,.48,.42,1]
    cellmesh(reg+'_Sculpted_Terrain',co,q['faces'],[terrainmat],groups['01_TERRAIN'],kind='terrain',color=colors)
    ring=np.asarray(islands[reg].exterior.coords);z=groundz(ring);v=[];f=[]
    for i,(aa,bb) in enumerate(zip(ring[:-1],ring[1:])):
        k=len(v);v.extend([[*aa,z[i]],[*bb,z[i+1]],[*bb,-4],[*aa,-4]]);f.extend([[k,k+1,k+2],[k,k+2,k+3]])
    cellmesh(reg+'_Coast_Skirt',v,f,[concrete],groups['01_TERRAIN'],kind='coast')
mesh('Sea_Excluded_From_Playable_Area',[[-2700,-2400,-.08],[2700,-2400,-.08],[2700,2400,-.08],[-2700,2400,-.08]],[[0,1,2],[0,2,3]],[water],groups['02_WATER'])
lt=shapely.get_parts(shapely.constrained_delaunay_triangles(lake));v=np.concatenate([np.c_[np.asarray(t.exterior.coords)[:3],np.full(3,9.96)] for t in lt]);mesh('West_Freshwater_Lake',v,np.arange(len(v)).reshape(-1,3),[lake_mat],groups['02_WATER'])
def prism(poly,top,bottom):
    poly=shapely.orient_polygons(poly,exterior_cw=False);xy=np.asarray(poly.exterior.coords)[:-1];n=len(xy);v=np.vstack([np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]]);f=[];mi=[]
    for j in range(1,n-1):f.extend([[0,j+1,j],[n,n+j,n+j+1]]);mi.extend([2,1])
    for j in range(n):k=(j+1)%n;f.extend([[j,k,k+n],[j,k+n,j+n]]);mi.extend([0,0])
    return v,np.asarray(f),mi
batch=collections.defaultdict(lambda:{'v':[],'f':[],'mi':[],'ids':[]});manifest=[]
for i,b in enumerate(p['buildings']):
    poly=Polygon(b['footprint']);base=b['base'];bottom=min(groundz(shapely.get_coordinates(poly)))-.35;h=b['height'];key=(b['region'],b['zone'],int(b['center'][0]//250),int(b['center'][1]//250));buf=batch[key]
    volumes=[(poly,base+min(h,10),bottom),(affinity.scale(poly,.60,.62,origin='centroid'),base+h,base+min(h,10))] if b['zone']=='CBD' else [(poly,base+h,bottom)]
    for poly0,top0,bot0 in volumes:
        if top0<=bot0:continue
        v,f,mi=prism(poly0,top0,bot0);off=len(buf['v']);buf['v'].extend(v.tolist());buf['f'].extend((f+off).tolist());buf['mi'].extend(mi);buf['ids'].extend([i]*len(f))
    manifest.append({'index':i,'name':b['name'],'batch':list(key),'base':base,'height':h})
for key,buf in batch.items():
    reg,zone,cx,cy=key;o=mesh(f'{reg}_{zone}_Massing_{cx}_{cy}',buf['v'],buf['f'],[buildmats[zone],roof,concrete],groups['05_BUILDING_PLACEHOLDERS'],mi=buf['mi'],lot=buf['ids']);o['is_placeholder']=True;o['placeholder_lot_count']=len(set(buf['ids']));o['region']=reg
print('PLACEHOLDERS_BUILT',len(manifest),'batches',len(batch),flush=True)
for r in p['real_buildings']:
    before=set(sc.objects);source=a.models/r['file'];bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update();imported=set(sc.objects)-before;parts=[o for o in imported if o.type=='MESH'];instance=empty(r['instance_name'],groups['07_SOURCE_BUILDINGS']);s=r['uniform_scale'];axis=r['local_axis_scale'];theta=r['theta'];instance.matrix_world=Matrix.Translation((*r['anchor'],r['floor']-.008))@Matrix.Rotation(theta,4,'Z')@Matrix.Translation((-r['left'],-r['front'],0))@Matrix.Rotation(r['turn'],4,'Z')@Matrix.Diagonal((*list(np.array(axis)*s),1.))@Matrix.Translation((0,0,-r['source_floor_reference']))
    for o in imported:
        if o.parent not in imported:
            old=o.matrix_world.copy();o.parent=instance;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=old
    instance['is_building_instance']=True;instance['source_filename']=r['file'];instance['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();instance['target_height_m']=r['target_height_m'];instance['corner_turn_degrees']=math.degrees(r['turn']);instance['direct_sidewalk_frontage']=r['direct_sidewalk_frontage'];instance['direct_alley_frontage']=bool(r.get('direct_alley_frontage'));instance['building_count_units']=int(r.get('building_count_units',1))
    for j,o in enumerate(parts):o.name=r['instance_name']+f'_Source_Mesh_{j:02d}';o['source_filename']=r['file']
    poly=Polygon(r['pad_xy']);v,f,_=prism(poly,r['floor']-.018,r['foundation_bottom_m']);mesh(r['instance_name']+'_Foundation',v,f,[concrete],groups['08_BUILDING_FOOTINGS']);print('SOURCE_PLACED',r['instance_name'],flush=True)
    if 'plaza_xy' in r:
        anchor=np.asarray(r['anchor']);theta=r['theta'];u=np.array([math.cos(theta),math.sin(theta)]);vdir=np.array([-u[1],u[0]]);width=r['right']-r['left'];depth=r['setback_m']+.05;verts=[];faces=[];uv=[]
        cuts=np.unique(np.r_[np.arange(0,width,2),np.arange(0,width,16.9048),width])
        for s0,s1 in zip(cuts[:-1],cuts[1:]):
            for d0 in np.arange(0,depth-.001,3):
                d1=min(depth,d0+3);local=np.array([[s0,d0],[s1,d0],[s1,d1],[s0,d1]]);xy=anchor+local[:,0,None]*u-local[:,1,None]*vdir;street=anchor+local[:,0,None]*u-depth*vdir;zstreet=gp.height(street)+.145577;t=local[:,1]/depth;z=(r['floor']-.008)*(1-t)+zstreet*t;k=len(verts);verts.extend(np.c_[xy,z].tolist());faces.extend([[k,k+2,k+1],[k,k+3,k+2]]);uu=(local[:,1]-d0)/3;vv=(local[:,0]-math.floor((s0+1e-7)/16.9048)*16.9048)/16.9048;uv.extend(np.c_[.271-.055*uu,.7766-.1777*vv].tolist())
        o=mesh(r['instance_name']+'_Entrance_Plaza',verts,faces,[roadmat],groups['08_BUILDING_FOOTINGS'],uv);o['surface_type']='source_access';o['access_width_m']=3.;o['central_access_grade']=abs((r['floor']-.008)-(gp.height([r['access_end_xy']])[0]+.145577))/depth
        boundary=np.asarray(shapely.segmentize(Polygon(r['plaza_xy']),max_segment_length=2).exterior.coords);sidev=[];sidef=[]
        for aa,bb in zip(boundary[:-1],boundary[1:]):
            xy=np.array([aa,bb]);ss=(xy-anchor)@u;dd=(anchor-xy)@vdir;street=anchor+ss[:,None]*u-depth*vdir;top=(r['floor']-.008)*(1-dd/depth)+(gp.height(street)+.145577)*(dd/depth);soil=groundz(xy);lo=np.minimum(soil-.25,top-.3);hi=np.maximum(top-.012,soil-.025);k=len(sidev);sidev.extend([[*aa,lo[0]],[*bb,lo[1]],[*bb,hi[1]],[*aa,hi[0]]]);sidef.extend([[k,k+1,k+2],[k,k+2,k+3]])
        mesh(r['instance_name']+'_Plaza_Retaining_Edges',sidev,sidef,[concrete],groups['08_BUILDING_FOOTINGS'])
row=[r for r in p['real_buildings'] if 'Connected_' in r['instance_name'] or 'Corner_Shop_10' in r['instance_name']]
for i,(l,r) in enumerate(zip(row[:-1],row[1:])):
    xx=r['anchor'][0];depth=min(l['rotated_xy_bounds'][1][1]-l['front'],r['rotated_xy_bounds'][1][1]-r['front']);poly=box(xx-.075,237.55,xx+.075,237.55+depth);top=min(l['floor']+l['target_height_m'],r['floor']+r['target_height_m'])-.6;v,f,_=prism(poly,top,min(l['floor'],r['floor'])-.2);mesh(f'Oldtown_Row_Partywall_{i:02d}',v,f,[seam],groups['08_BUILDING_FOOTINGS'])
joined=[r for r in p['real_buildings'] if r['instance_name'].startswith('OLDTOWN_Joined_')]
if len(joined)==2:
    l,r=joined;xx=r['anchor'][0];y0=max(Polygon(q['footprint_xy']).bounds[1] for q in joined);y1=min(Polygon(q['footprint_xy']).bounds[3] for q in joined);v,f,_=prism(box(xx-.075,y0+.07,xx+.075,y1-.07),min(q['floor']+q['target_height_m'] for q in joined)-.65,l['floor']-.15);mesh('Oldtown_Joined_12_13_Partywall',v,f,[seam],groups['08_BUILDING_FOOTINGS'])
# Straight engineered pedestrian profiles, original sidewalk atlas, cut-and-fill beds.
walkreport=[]
for r in p['pedestrian_alleys']:
    aa,bb=np.array(r['points']);length=np.linalg.norm(bb-aa);tangent=(bb-aa)/length;n=np.array([-tangent[1],tangent[0]]);vv=[];ff=[];uv=[];sidev=[];sidef=[]
    for start in np.arange(0,length-.001,16.9048):
        stop=min(length,start+16.9048);cuts=np.linspace(start,stop,max(2,int((stop-start)/2)+1));off=len(vv)
        for s0 in cuts:
            center=aa+tangent*s0;z=np.interp(s0,[0,length],r['end_heights']);pair=center[None,:]+np.array([-1,1])[:,None]*n*r['width']/2;vv.extend(np.c_[pair,[z,z]].tolist());uv.extend([[.271,.7766-.1777*(s0-start)/16.9048],[.216,.7766-.1777*(s0-start)/16.9048]])
        for k in range(len(cuts)-1):j=off+k*2;ff.extend([[j,j+1,j+3],[j,j+3,j+2]])
    # Winding depends on tangent x normal; normalize every triangle to face up.
    v=np.array(vv);f=np.array(ff);tr=v[f];det=np.cross(tr[:,1]-tr[:,0],tr[:,2]-tr[:,0])[:,2];f[det<0]=f[det<0,::-1];o=mesh(r['name'],v,f,[roadmat],groups['10_PEDESTRIAN_NETWORK'],uv);o['surface_type']='pedestrian';o['maximum_grade']=r['max_grade']
    rect=Polygon(np.vstack([aa+n*1.8,bb+n*1.8,bb-n*1.8,aa-n*1.8]));boundary=np.asarray(shapely.segmentize(rect,max_segment_length=3).exterior.coords);foot=groundz(boundary);retaining=0
    for k,(q0,q1) in enumerate(zip(boundary[:-1],boundary[1:])):
        stations=np.array([(q-aa)@tangent for q in [q0,q1]]);zz=np.interp(stations,[0,length],r['end_heights']);soil=foot[k:k+2];lower=np.minimum(soil-.2,zz-.22);upper=np.maximum(soil-.035,zz-.015);retaining=max(retaining,float(np.max(upper-lower)));j=len(sidev);sidev.extend([[*q0,lower[0]],[*q1,lower[1]],[*q1,upper[1]],[*q0,upper[0]]]);sidef.extend([[j,j+1,j+2],[j,j+2,j+3]])
    mesh(r['name']+'_Cut_Fill_Bed',sidev,sidef,[concrete],groups['10_PEDESTRIAN_NETWORK']);walkreport.append({'name':r['name'],'maximum_grade':r['max_grade'],'maximum_retaining_height_m':retaining})
# Elevated concrete decks and parapets are separate from their textured road surfaces.
groundfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in p['edges'] if e['layer'].startswith('GROUND')]);deckbuf=collections.defaultdict(lambda:{'v':[],'f':[]});railbuf=collections.defaultdict(lambda:{'v':[],'f':[]});piers=[]
def append(buf,v,f):off=len(buf['v']);buf['v'].extend(np.asarray(v).tolist());buf['f'].extend((np.asarray(f)+off).tolist())
for ei,e in enumerate(p['edges']):
    if not (e['bridge'] or e['layer'].startswith('IX')):continue
    branch_footprints=[]
    for ni in [e['a'],e['b']]:
        if len(p['nodes'][ni]['edges'])<3:continue
        for otherid in p['nodes'][ni]['edges']:
            other=p['edges'][otherid]
            if other['name']==e['name']:continue
            branch_footprints.append(LineString(np.asarray(other['points'])[:,:2]).buffer(other['width']/2+.4,quad_segs=4))
    rail_openings=unary_union(branch_footprints) if branch_footprints else None
    co=np.asarray(e['points']);L=e['length'];dd=np.r_[0,np.cumsum(np.linalg.norm(np.diff(co[:,:2],axis=0),axis=1))];support=groundz(co[:,:2]);elev=co[:,2]-support;use=np.ones(len(co)-1,bool)
    for k in np.flatnonzero(use):
        c0,c1=co[k],co[k+1];vec=c1[:2]-c0[:2];n=np.array([-vec[1],vec[0]])/np.linalg.norm(vec);w=e['width']/2;xy=np.array([c0[:2]-n*w,c1[:2]-n*w,c1[:2]+n*w,c0[:2]+n*w]);top=np.array([c0[2],c1[2],c1[2],c0[2]])-.035;v=np.vstack([np.c_[xy,top-1.1],np.c_[xy,top]]);f=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]);cell=tuple(np.floor((c0[:2]+c1[:2])/500).astype(int));key=(e['bridge'],*cell);append(deckbuf[key],v,f)
        for side in [-1,1]:
            xy0=c0[:2]+n*(side*(w-.18));xy1=c1[:2]+n*(side*(w-.18))
            rail_line=LineString([xy0,xy1]);open_join=rail_openings is not None and rail_line.intersects(rail_openings)
            if (e['bridge'] or max(elev[k],elev[k+1])>1.25) and not open_join:
                xyrail=np.array([xy0-n*.11,xy1-n*.11,xy1+n*.11,xy0+n*.11]);zr=np.array([c0[2],c1[2],c1[2],c0[2]]);v=np.vstack([np.c_[xyrail,zr+.13],np.c_[xyrail,zr+1.05]]);append(railbuf[key],v,f)
            if not e['bridge']:
                xy0=c0[:2]+n*(side*w);xy1=c1[:2]+n*(side*w);soil=groundz([xy0,xy1]);zz=np.array([c0[2],c1[2]])+.14
                if max(soil-zz)>.03:
                    top=np.maximum(soil-.01,zz-.02);v=np.array([[*xy0,zz[0]-.35],[*xy1,zz[1]-.35],[*xy1,top[1]],[*xy0,top[0]]]);append(deckbuf[key],v,[[0,1,2],[0,2,3]])
    for station in np.arange(26,L-20,34):
        c,n=frame(e,station);z=float(c[2]-1.135);base=-4. if e['bridge'] else float(groundz([c[:2]])[0])-.4
        if z-base<2.1:continue
        if not e['bridge'] and Point(c[:2]).buffer(1.1).intersects(groundfull):continue
        poly=box(c[0]-.65,c[1]-.65,c[0]+.65,c[1]+.65);v,f,_=prism(poly,z,base);name=('BRIDGES' if e['bridge'] else 'MAIN')+f'_Pier_{ei:03d}_{int(station):04d}';o=mesh(name,v,f,[concrete],groups['04_BRIDGE_STRUCTURES'] if e['bridge'] else groups['09_CITY_INTERCHANGES']);o['surface_type']='pier';piers.append({'name':name,'xy':c[:2].tolist(),'radius':.92,'bridge':e['bridge']})
for prefix,bufs,mat in [('Deck',deckbuf,concrete),('Parapet',railbuf,railmat)]:
    for (bridge,cx,cy),buf in bufs.items():mesh(('BRIDGES' if bridge else 'MAIN')+f'_{prefix}_{cx}_{cy}',buf['v'],buf['f'],[mat],groups['04_BRIDGE_STRUCTURES'] if bridge else groups['09_CITY_INTERCHANGES'])
bpy.context.view_layer.update()
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
        try:im.pack()
        except RuntimeError:pass
report={'schema':'hero13.city.compact-build.v10','stats':p['stats'],'massing_batches':len(batch),'mesh_objects':sum(o.type=='MESH' for o in sc.objects),'pedestrian_walkways':walkreport,'piers':piers,'original_source_buildings':len(p['real_buildings']),'building_count':len(p['buildings'])+sum(r.get('building_count_units',1) for r in p['real_buildings']),'added_canopy':False}
(a.out/'compact_build_report.json').write_text(json.dumps(report,indent=2));(a.out/'massing_manifest.json').write_text(json.dumps(manifest,separators=(',',':')));(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((a.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain their textures.')
print('COMPACT_CITY_BUILT',json.dumps({'glb_bytes':(a.out/'huizhou_road_network.glb').stat().st_size,**p['stats']}),flush=True)
