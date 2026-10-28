"""Replace every v10 rear-house site with linked, metrically placed source assets."""
import bpy,sys,json,math,hashlib,collections,heapq,shutil,csv,argparse
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,default=ROOT/'recovery/huizhou_city_v10');ap.add_argument('--out',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--models',type=Path,default=ROOT/'work_v11/source/buildings');ap.add_argument('--uploads',type=Path,default=ROOT/'upload');ap.add_argument('--deps',type=Path,default=ROOT/'blender_deps');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
sys.path.insert(0,str(args.deps.resolve()))
sys.path.insert(0,str(args.baseline.resolve()/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,nearest_points
from city_surface_sampling import HeightField
OLD=args.baseline.resolve();OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
SRC=args.models.resolve();SRC.mkdir(parents=True,exist_ok=True)
for f in (OLD/'source/buildings').glob('*.glb'):
    if not (SRC/f.name).exists():shutil.copy2(f,SRC/f.name)
files={20:'urban_building_facade_20.glb',19:'old_italian_townhouse_19.glb',18:'apartment_building_18.glb',17:'old_building_17.glb',15:'historic_building_facade_15.glb'}
for k,name in files.items():
    if not (SRC/name).exists():shutil.copy2(next(args.uploads.glob(f'*-{k}.glb')),SRC/name)
files.update({13:'old_apartment_13.glb',14:'apartment_14.glb'})
heights={20:10.8,19:11.1,18:12.0,17:10.6,15:10.7,13:16.0,14:16.4}
p=json.loads((OLD/'city_plan.json').read_text());oldp=json.loads((OLD/'city_plan.json').read_text())
oldsites=[(i,b) for i,b in enumerate(p['buildings']) if b['typology']=='backlane_house'];assert len(oldsites)==35
bpy.ops.wm.open_mainfile(filepath=str(OLD/'huizhou_road_network.blend'));sc=bpy.context.scene;bpy.context.view_layer.update()
root=bpy.data.objects['Huizhou_Reconstructed_City_3p25km2'];sourceparent=bpy.data.objects['07_SOURCE_BUILDINGS'];footparent=bpy.data.objects['08_BUILDING_FOOTINGS'];walkparent=bpy.data.objects['10_PEDESTRIAN_NETWORK']
root['version']='v11_all_backlanes_replaced';root['building_limit']=699
oldobjects=[o for o in sc.objects if o.type=='MESH']
terrain_objects=[o for o in oldobjects if o.get('surface_type')=='terrain'];terrain=HeightField(terrain_objects)
originalwalks=[o for o in oldobjects if o.get('surface_type') in ['sidewalk','pedestrian_walkway'] or o.name in {a['name'] for a in p['pedestrian_alleys']}]
walkfield=HeightField(originalwalks)
concrete=bpy.data.materials['Bridge_Concrete'];roadmat=bpy.data.materials['Road_Modular_Original_Atlas'];seammat=bpy.data.materials['Oldtown_Seam_Plaster']
def mesh(name,v,f,mat,parent,uv=False):
    m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=parent
    if uv:
        layer=m.uv_layers.new(name='UVMap')
        for poly in m.polygons:
            for li in poly.loop_indices:
                co=m.vertices[m.loops[li].vertex_index].co;layer.data[li].uv=(.216+.055*((co.x/3)%1),.5989+.1777*((co.y/16.9048)%1))
    return o
def prism(poly,top,bottom,name,parent=footparent,mat=concrete):
    poly=shapely.orient_polygons(poly,exterior_cw=False)
    xy=np.asarray(poly.exterior.coords)[:-1];n=len(xy);v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];f=[]
    for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
    for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
    return mesh(name,v.tolist(),f,mat,parent)
templates={}
for key,file in files.items():
    before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(SRC/file));bpy.context.view_layer.update();imported=set(sc.objects)-before;parts=[]
    for obj in imported:
        if obj.type!='MESH':continue
        data=obj.data.copy();data.transform(obj.matrix_world);parts.append(data)
    allco=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=allco.min(0);hi=allco.max(0)
    templates[key]={'parts':parts,'lo':lo,'hi':hi,'dimensions':hi-lo,'file':file}
    for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
    print('TEMPLATE',key,(hi-lo).tolist(),flush=True)
sites=[(i,b) for i,b in oldsites if b['block_id']!=68];assert len(sites)==33
retained=[Polygon(b['footprint']) for b in p['buildings'] if b['typology']!='backlane_house']+[Polygon(r['footprint_xy']) for r in p['real_buildings']]
obstacles=unary_union(retained)
carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.1) for e in p['edges'] if e['layer'].startswith('GROUND')])
land=unary_union([Polygon(v) for v in p['coasts'].values()]).difference(Polygon(p['lake']))
goals=[]
for a in p['pedestrian_alleys']:goals.append({'name':a['name'],'line':LineString(a['points']),'kind':'alley'})
for e in p['edges']:
    if e['region']!='MAIN' or not e['layer'].startswith('GROUND'):continue
    line=LineString(np.array(e['points'])[:,:2])
    if line.bounds[1]>600 or line.bounds[3]<-20:continue
    for side in ['left','right']:
        goal=line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.5,side,join_style=2)
        if goal.geom_type=='LineString':goals.append({'name':e['name']+'_'+side,'line':goal,'kind':'sidewalk'})
def clear(coords,blocked,margin=1.87):
    line=LineString(coords)
    nav=line.buffer(margin,cap_style=2,join_style=2)
    return (not blocked.intersects(nav) or nav.intersection(blocked).area<1e-5) and land.covers(nav)
def routes(start,blocked):
    options=[]
    for g in sorted(goals,key=lambda g:g['line'].distance(Point(start)))[:20]:
        projection=g['line'].project(Point(start));s=np.array(start)
        for offset in [0,-8,8,-16,16,-24,24,-36,36,-50,50]:
            end=np.array(g['line'].interpolate(np.clip(projection+offset,0,g['line'].length)).coords[0])
            candidates=[[s,end],[s,np.array([s[0],end[1]]),end],[s,np.array([end[0],s[1]]),end]]
            for co in candidates:
                co=np.array([co[i] for i in range(len(co)) if i==0 or np.linalg.norm(np.array(co[i])-co[i-1])>.01])
                if len(co)<2:continue
                if clear(co,blocked):options.append((LineString(co).length,g,co))
    return sorted(options,key=lambda x:x[0])
preblocked=unary_union([obstacles,carriage]);shapely.prepare(preblocked);shapely.prepare(land);rows=[]
core={'name':'REAR_068_Original_Extension','block_id':68,'keys':[20,19,18,17,15],'face':[244.45,261.825],'u':[1.,0.],'n':[0.,-1.],'site_names':[b['name'] for i,b in oldsites if b['block_id']==68],'available':95.,'core':True};rows.append(core)
for j,(index,b) in enumerate(sites):
    opts=routes(b['center'],preblocked)
    if not opts:raise RuntimeError(('rear site has no pedestrian exit',b['name']))
    _,g,co=opts[0];delta=co[1]-co[0];axis=int(np.argmax(abs(delta)));n=np.zeros(2);n[axis]=np.sign(delta[axis]);u=np.array([-n[1],n[0]])
    poly=Polygon(b['footprint']);xy=np.array(poly.exterior.coords)[:-1];extent=(xy-np.array(b['center']))@n;available=float(np.ptp(xy@u))-.5
    face=np.array(b['center'])+n*float(max(extent));keys=([13,14,15][(j//3)%3:][:1] if j%3==0 else [[20,19],[18,17],[19,18],[17,20]][j%4])
    assert len(keys) in [1,2]
    rows.append({'name':f'REAR_{b["block_id"]:03d}_{index:03d}','block_id':b['block_id'],'keys':keys,'face_center':face.tolist(),'u':u.tolist(),'n':n.tolist(),'available':available,'site_names':[b['name']],'core':False})
placed=[]
for ri,row in enumerate(rows):
    u=np.array(row['u']);n=np.array(row['n']);theta=math.atan2(u[1],u[0]);variants=[]
    for k,key in enumerate(row['keys']):
        t=templates[key];height=heights[key]*(1.0 if row['core'] else [1.,.98,1.025,.99][(ri+k)%4]);s=height/t['dimensions'][2];variants.append({'key':key,'height':height,'scale':s,'width':t['dimensions'][0]*s,'depth':t['dimensions'][1]*s})
    width=sum(q['width'] for q in variants)+.12*(len(variants)-1);factor=min(1.,row['available']/width)
    assert factor>.9,('source stretched too far',row['name'],factor)
    for q in variants:q['width']*=factor;q['axis_scale']=[factor,1.,1.]
    width=sum(q['width'] for q in variants)+.12*(len(variants)-1)
    left=np.array(row['face']) if row['core'] else np.array(row['face_center'])-u*width/2
    row['face']=left.tolist();row['width']=width;row['instances']=[];pos=0.
    for k,q in enumerate(variants):
        anchor=left+u*pos;xy=np.array([anchor,anchor+u*q['width'],anchor+u*q['width']-n*q['depth'],anchor-n*q['depth']]);poly=Polygon(xy);name=f'OLDTOWN_Rear_{ri:02d}_{k+1:02d}_Asset{q["key"]}'
        r={'instance_name':name,'file':files[q['key']],'source_filename':files[q['key']],'source_key':q['key'],'uniform_scale':q['scale'],'local_axis_scale':q['axis_scale'],'target_height_m':q['height'],'source_bounds':[templates[q['key']]['lo'].tolist(),templates[q['key']]['hi'].tolist()],'source_floor_reference':float(templates[q['key']]['lo'][2]),'turn':0.,'left':0.,'right':q['width'],'front':0.,'anchor':anchor.tolist(),'theta':theta,'angle':math.degrees(theta),'center':poly.centroid.coords[0],'region':'MAIN','footprint_xy':xy.tolist(),'pad_xy':poly.buffer(.10,join_style=2).exterior.coords[:],'direct_sidewalk_frontage':False,'direct_alley_frontage':True,'access_alley':row['name']+'_Entry_Walk','building_count_units':1,'typology':'backlane_source_house','replaces_placeholder_sites':row['site_names'],'reuse_rotation_only_no_mirror':True,'row_name':row['name']}
        if poly.intersection(obstacles).area>1e-5:raise RuntimeError(('source intersects retained building',name,poly.intersection(obstacles).area))
        if poly.intersection(carriage).area>1e-5:raise RuntimeError(('source in carriageway',name))
        placed.append(r);row['instances'].append(r);pos+=q['width']+.12
assert len(placed)==60
allpolys=retained+[Polygon(r['footprint_xy']) for r in placed];tree=shapely.STRtree(allpolys)
for i in range(len(retained),len(allpolys)):
    for j in tree.query(allpolys[i]):
        if j>=i:continue
        if allpolys[i].intersection(allpolys[j]).area>1e-5:raise RuntimeError(('new buildings overlap',i,int(j)))
blocked=unary_union([*allpolys,carriage]);shapely.prepare(blocked);paving=[];connections=[]
for row in rows:
    face=np.array(row['face']);u=np.array(row['u']);n=np.array(row['n']);width=row['width'];start=face+u*width/2+n*(.10 if row['core'] else 2.1)
    opts=routes(start,blocked)
    if not opts:raise RuntimeError(('frontage has no pedestrian exit',row['name'],start.tolist()))
    dist,g,coords=opts[0];goal=np.array(coords[-1]);goalz=walkfield.height(goal)
    if goalz is None:raise RuntimeError(('goal lacks actual walk surface',row['name'],g['name'],goal.tolist()))
    soil=terrain.height(start);dist=max(.1,dist);rise=max(0.,dist-4.5)*.025;floor=float(goalz+.028 if row['core'] else goalz+.028+np.clip((soil if soil is not None else goalz)-goalz,-rise,rise))
    foredepth=.20 if row['core'] else 3.90
    fore=Polygon([face-u*.02,face+u*(width+.02),face+u*(width+.02)+n*foredepth,face-u*.02+n*foredepth]);route=LineString(coords);poly=unary_union([fore,route.buffer(1.8,cap_style=2,join_style=2)])
    if poly.intersection(unary_union(allpolys)).area>.002:raise RuntimeError(('paving intersects building',row['name'],poly.intersection(unary_union(allpolys)).area))
    # Narrow neck joins a real, already connected walk surface. The full frontage is paved.
    row.update(floor=floor,goal=goal.tolist(),goal_z=goalz,goal_name=g['name'],route=coords.tolist(),polygon=poly.exterior.coords[:])
    for r in row['instances']:
        r['floor']=floor;pad=Polygon(r['pad_xy']);zz=[terrain.height(q) for q in shapely.segmentize(pad,2).exterior.coords];zz=[z for z in zz if z is not None];r['foundation_bottom_m']=float(min([floor-.45,*zz])-.12)
    paving.append(poly)
    connections.append({'name':row['name'],'goal_name':g['name'],'goal_kind':g['kind'],'points':coords.tolist(),'width':3.6,'length':route.length,'floor':floor,'goal_z':goalz,'longitudinal_grade':abs((floor-.028)-goalz)/dist,'source_buildings':[r['instance_name'] for r in row['instances']]})
print('LAYOUT_READY',len(placed),'instances in',len(rows),'rows',flush=True)
# Delete all 35 placeholder identities, keeping every unrelated face and roof height.
removed={i for i,b in oldsites};mapping={old:new for new,old in enumerate(i for i in range(len(p['buildings'])) if i not in removed)};deleted_faces=0
for ob in list(sc.objects):
    if ob.type!='MESH':continue
    attr=ob.data.attributes.get('source_building_index')
    if not attr:continue
    m=ob.data;ids=np.array([v.value for v in attr.data]);keep=~np.isin(ids,list(removed));deleted_faces+=int((~keep).sum())
    if not keep.any():bpy.data.objects.remove(ob,do_unlink=True);continue
    faces=[list(poly.vertices) for poly,k in zip(m.polygons,keep) if k];mats=[poly.material_index for poly,k in zip(m.polygons,keep) if k];newids=[mapping[int(i)] for i,k in zip(ids,keep) if k]
    if keep.all():
        attr.data.foreach_set('value',np.array(newids,np.int32))
    else:
        data=bpy.data.meshes.new(m.name+'_v11');data.from_pydata([v.co[:] for v in m.vertices],[],faces)
        for mat in m.materials:data.materials.append(mat)
        data.polygons.foreach_set('material_index',np.array(mats,np.int32));data.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',np.array(newids,np.int32));data.update();ob.data=data
    ob['placeholder_lot_count']=len(set(newids))
p['buildings']=[b for i,b in enumerate(p['buildings']) if i not in removed]
for row in rows:
    for r in row['instances']:
        t=templates[r['source_key']];instance=bpy.data.objects.new(r['instance_name'],None);sc.collection.objects.link(instance);instance.parent=sourceparent
        instance.matrix_world=Matrix.Translation((*r['anchor'],r['floor']-.008))@Matrix.Rotation(r['theta'],4,'Z')@Matrix.Diagonal((*list(np.array(r['local_axis_scale'])*r['uniform_scale']),1.))@Matrix.Translation(tuple(-t['lo']))
        for j,data in enumerate(t['parts']):
            o=bpy.data.objects.new(r['instance_name']+f'_Source_Mesh_{j:02d}',data);sc.collection.objects.link(o);o.parent=instance;o.matrix_basis=Matrix.Identity(4);o['source_filename']=r['file']
        for k,v in {'is_building_instance':True,'source_filename':r['file'],'source_sha256':hashlib.sha256((SRC/r['file']).read_bytes()).hexdigest(),'target_height_m':r['target_height_m'],'direct_sidewalk_frontage':False,'direct_alley_frontage':True,'building_count_units':1,'reuse_template_key':r['source_key'],'reuse_linked_mesh':True}.items():instance[k]=v
        prism(Polygon(r['pad_xy']),r['floor']-.018,r['foundation_bottom_m'],r['instance_name']+'_Foundation')
    # One continuous frontage and connecting path per row, with the road kit's atlas.
    poly=shapely.segmentize(Polygon(row['polygon']),1.8);tri=shapely.get_parts(shapely.constrained_delaunay_triangles(poly));v=[];f=[];route=LineString(row['route']);L=route.length;floor=row['floor']-.028;goalz=row['goal_z'];face=np.array(row['face']);u=np.array(row['u']);n=np.array(row['n']);maxgrade=0
    def walkz(xy):
        xy=np.array(xy);s=route.project(Point(xy));z=floor+(goalz-floor)*s/max(L,.001)
        infore=(-.03<np.dot(xy-face,u)<row['width']+.03 and -.03<np.dot(xy-face,n)<(.21 if row['core'] else 3.91))
        if infore:z=floor
        oldz=walkfield.height(xy)
        if oldz is not None and (row['core'] or np.linalg.norm(xy-np.array(row['goal']))<3.8):z=oldz+.003
        return z
    for t in tri:
        xy=np.array(t.exterior.coords)[:3];a=xy[1]-xy[0];b=xy[2]-xy[0]
        if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
        k=len(v);v.extend([[*q,walkz(q)] for q in xy]);f.append([k,k+1,k+2])
    o=mesh(row['name']+'_Entry_Walk',v,f,roadmat,walkparent,True);o['surface_type']='backlane_entry_walk';o['connects_to']=row['goal_name'];o['clear_width_m']=3.6
    # Closed retaining edges prevent visible open cuts where the lane crosses a slope.
    verts=[];faces=[]
    for a,b in zip(poly.exterior.coords[:-1],poly.exterior.coords[1:]):
        za=walkz(a);zb=walkz(b);sa=terrain.height(a);sb=terrain.height(b);ba=min(za-.18,(sa if sa is not None else za)-.12);bb=min(zb-.18,(sb if sb is not None else zb)-.12);k=len(verts);verts.extend([[*a,ba],[*b,bb],[*b,zb-.012],[*a,za-.012]]);faces.extend([[k,k+1,k+2],[k,k+2,k+3]])
    mesh(row['name']+'_Walk_Retaining_Edges',verts,faces,concrete,footparent)
    for a,b in zip(row['instances'][:-1],row['instances'][1:]):
        aa=np.array(a['anchor'])+u*a['right'];bb=np.array(b['anchor']);depth=min(templates[a['source_key']]['dimensions'][1]*a['uniform_scale'],templates[b['source_key']]['dimensions'][1]*b['uniform_scale']);poly=Polygon([aa,bb,bb-n*depth,aa-n*depth]);prism(poly,row['floor']+min(a['target_height_m'],b['target_height_m'])-.25,row['floor']-.018,'Rear_Partywall_'+a['instance_name'],footparent,seammat)
print('BUILDINGS_AND_ACCESS_BUILT',flush=True)
# Cut only the newly occupied terrain triangles. Existing road surfaces and all other terrain stay exact.
cutter=unary_union([Polygon(r['pad_xy']) for r in placed]+[poly.buffer(.015,join_style=2) for poly in paving]);clipped=0;terrain_changed=[]
for ob in terrain_objects:
    m=ob.data;m.calc_loop_triangles();co=np.array([v.co[:] for v in m.vertices]);tri=np.array([t.vertices[:] for t in m.loop_triangles]);centers=co[tri,:2].mean(1)
    bbox=box(float(co[:,0].min()),float(co[:,1].min()),float(co[:,0].max()),float(co[:,1].max()))
    local=cutter.intersection(bbox)
    if local.is_empty:continue
    newv=[];newf=[];oldcolors=None
    if m.color_attributes:oldcolors=np.array([c.color[:] for c in m.color_attributes[0].data])
    newcolors=[];changes=0
    for indices in tri:
        xyz=co[indices];q=Polygon(xyz[:,:2])
        if not q.intersects(local):parts=[xyz]
        else:
            diff=q.difference(local)
            if q.area-diff.area<1e-8:parts=[xyz]
            else:
                changes+=1;parts=[]
                if not diff.is_empty:
                    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
                        xy=np.array(t.exterior.coords)[:3];A=np.vstack([xyz[:,:2].T,np.ones(3)]);weights=np.linalg.solve(A,np.vstack([xy.T,np.ones(3)]));parts.append(np.c_[xy,weights.T@xyz[:,2]])
        for part in parts:
            a=part[1,:2]-part[0,:2];b=part[2,:2]-part[0,:2]
            if a[0]*b[1]-a[1]*b[0]<0:part=part[::-1]
            k=len(newv);newv.extend(part.tolist());newf.append([k,k+1,k+2])
            if oldcolors is not None:
                A=np.vstack([xyz[:,:2].T,np.ones(3)]);B=np.vstack([part[:,:2].T,np.ones(3)])
                if np.array_equal(part,xyz):colors=oldcolors[indices]
                else:
                    try:weights=np.linalg.solve(A,B)
                    except np.linalg.LinAlgError:weights=np.linalg.lstsq(A,B,rcond=None)[0]
                    colors=weights.T@oldcolors[indices]
                newcolors.extend(colors.tolist())
    if not changes:continue
    data=bpy.data.meshes.new(m.name+'_RearCuts');data.from_pydata(newv,[],newf)
    for mat in m.materials:data.materials.append(mat)
    if newcolors:data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(newcolors,np.float32).ravel())
    data.update();ob.data=data;clipped+=changes;terrain_changed.append(ob.name)
    print('TERRAIN_REAR_CUT',ob.name,changes,flush=True)
p['real_buildings'].extend(placed);p['rear_access_links']=connections;p['rear_rows']=[{k:v for k,v in r.items() if k!='instances'} for r in rows];p['schema']='hero13.city.backlanes.v11';p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),backlane_placeholder_lots=0,backlane_asset_instances=62,replaced_backlane_sites=35,added_backlane_access_links=len(rows));p['stats']['building_count_by_zone']['OLDTOWN']+=25
assert p['stats']['buildings']==665<700;root['building_count']=665
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
        try:im.pack()
        except RuntimeError:pass
build=json.loads((OLD/'validation/compact_build_report.json').read_text());build.update(schema='hero13.city.backlane-build.v11',stats=p['stats'],original_source_buildings=75,building_count=665,rear_sites_replaced=35,rear_instances_added=60,rear_instances_total=62,source_asset_types=20,rear_asset_types=7,reuse_counts=dict(collections.Counter(r['source_key'] for r in placed)),placeholder_faces_removed=deleted_faces,terrain_triangles_cut=clipped,terrain_cells_changed=terrain_changed)
report={'status':'built','all_35_rear_placeholders_removed':True,'instances_added':60,'rear_instances_including_existing':62,'total_city_buildings':665,'linked_mesh_reuse':True,'sources':dict(collections.Counter(r['source_key'] for r in placed)),'connections':connections,'land_area_unchanged_m2':p['stats']['land_area_m2'],'retained_original_assets':15}
(OUT/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(OUT/'compact_build_report.json').write_text(json.dumps(build,indent=2));(OUT/'rear_replacement_report.json').write_text(json.dumps(report,indent=2));(OUT/'rear_source_descriptors.json').write_text(json.dumps(placed,indent=2))
with (OUT/'building_registry.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['id','kind','zone','typology','source_file','source_key','x','y','height_m','row','count_units']);w.writeheader()
    for b in p['buildings']:w.writerow({'id':b['name'],'kind':'placeholder','zone':b['zone'],'typology':b['typology'],'x':b['center'][0],'y':b['center'][1],'height_m':b['height'],'count_units':1})
    for r in p['real_buildings']:w.writerow({'id':r['instance_name'],'kind':'source','zone':'CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN','typology':r.get('typology','retained_source'),'source_file':r['file'],'source_key':r.get('source_key',''),'x':r['center'][0],'y':r['center'][1],'height_m':r['target_height_m'],'row':r.get('row_name',''),'count_units':1})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain their textures.')
print('V11_BUILT',665,(OUT/'huizhou_road_network.glb').stat().st_size,flush=True)
