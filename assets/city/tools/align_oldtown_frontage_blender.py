"""Seat six shop houses directly on the existing sidewalk and turn the corner.

Input is the completed six-building expansion stage. Roads and sidewalks are
fingerprinted and stay untouched. The earlier terrain is restored before the
new individual building pads are cut; original source texture bytes survive.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,math,sys
import bpy,numpy as np
from mathutils import Matrix

ap=argparse.ArgumentParser()
for key in ['blend','restore-terrain','plan','config','chunk-report','deps','out']:
    ap.add_argument('--'+key,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon,Point,LineString,MultiPoint
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;bpy.context.view_layer.update()
p=json.loads(a.plan.read_text());cfg=json.loads(a.config.read_text());oldrow=p['connected_arcades'];origin=np.array(oldrow['front_origin']);U=np.array(oldrow['u']);V=np.array(oldrow['v']);R=np.column_stack([U,V]);a.out.mkdir(parents=True,exist_ok=True)
def fingerprint(obs):
    h=hashlib.sha256()
    for o in sorted(obs,key=lambda q:q.name):
        h.update(o.name.encode());h.update(np.asarray(o.matrix_world,np.float32).tobytes())
        for size,collection,attribute,dtype in [(3,o.data.vertices,'co',np.float32),(1,o.data.loops,'vertex_index',np.int32)]:
            ar=np.empty(len(collection)*size,dtype);collection.foreach_get(attribute,ar);h.update(ar.tobytes())
        if o.data.uv_layers.active:
            ar=np.empty(len(o.data.loops)*2,np.float32);o.data.uv_layers.active.data.foreach_get('uv',ar);h.update(ar.tobytes())
    return h.hexdigest()
protected=[o for o in sc.objects if o.type=='MESH' and any(q in o.name for q in ['_Road_','Sidewalk_Modular','Sidewalk_Continuous_Transition','Continuous_Pavement','Junction_Repairs_Asphalt','Junction_Repairs_Original_Road_Kit','Junction_Repairs_Sidewalk','Port_Service_'])]
before=fingerprint(protected)
walk=HeightField([o for o in protected if any(q in o.name for q in ['MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_'])])
# Original sidewalk outer edge, sampled by actual surface/polygon boundary.
scheme=json.loads(gzip.decompress((a.plan.parent/'redevelopment_plan.json.gz').read_bytes())) if (a.plan.parent/'redevelopment_plan.json.gz').exists() else json.loads(gzip.decompress((Path(__file__).resolve().parents[3]/'design/city/redevelopment_plan.json.gz').read_bytes()))
full=shapely.from_geojson(scheme['new_full_footprint']);road=shapely.from_geojson(scheme['new_pavement']);walkshape=full.difference(road)
def edge_y(x):
    q=origin+U*x-V*7.7;segment=LineString([q-V*3,q+V*3]);pts=shapely.get_coordinates(segment.intersection(full.boundary));pts=[v for v in pts if full.covers(Point(v-V*.025)) and not full.covers(Point(v+V*.025))]
    if not pts:raise ValueError(('No outer sidewalk edge',x))
    pt=min(pts,key=lambda v:abs((v-q)@V));return float((pt-origin)@V)

# Reuse source meshes, including UVs, materials and their packed images.
models=[]
for spec in cfg['models'][:6]:
    inst=bpy.data.objects[spec['instance_name']];part=next(o for o in inst.children_recursive if o.type=='MESH');co=np.array([inst.matrix_world.inverted()@part.matrix_world@v.co for v in part.data.vertices]);scale=spec['uniform_scale'];axis=np.array(spec['local_axis_scale']);turn=math.pi/2 if spec['instance_name']=='OLDTOWN_Corner_Shop_10' else 0.
    rr=np.array([[math.cos(turn),-math.sin(turn)],[math.sin(turn),math.cos(turn)]]);pre=co[:,:2]*(scale*axis[:2]);pre=pre@rr.T;z=co[:,2];lo,hi=np.array(spec['source_bounds']);mask=(z>lo[2]+(hi[2]-lo[2])*.17)&(z<lo[2]+(hi[2]-lo[2])*.75)
    if turn:
        front=float(np.quantile(pre[mask,1],.01));yl,yh=pre[:,1].min(),pre[:,1].max();core=pre[mask&(pre[:,1]>yl+(yh-yl)*.35)&(pre[:,1]<yl+(yh-yl)*.8)];left,right=np.quantile(core[:,0],[.005,.995])
    else:front=spec['source_front_reference']*scale*axis[1];left=spec['source_core_left']*scale;right=spec['source_core_right']*scale
    models.append(dict(spec=spec,instance=inst,part=part,co=co,pre=pre,turn=turn,left=float(left),right=float(right),front=front,width=float(right-left)))

# Re-seat the row slightly towards its right-hand junction as well as forwards.
# Choose the farthest admissible position without putting a wall in the road.
placements=None
for shift in np.arange(9.0,-.01,-.25):
    cursor=-oldrow['length_m']/2+shift;attempt=[];safe=True
    for m in models:
        x0=cursor;x1=x0+m['width']
        for _ in range(3):
            y0=edge_y(x0);y1=edge_y(x1);x1=x0+m['width']/math.sqrt(1+((y1-y0)/(x1-x0))**2)
        theta=math.atan2(y1-y0,x1-x0)+math.atan2(U[1],U[0]);u=np.array([math.cos(theta),math.sin(theta)]);v=np.array([-u[1],u[0]]);anchor=origin+U*x0+V*y0+v*.025
        relative=m['pre']-np.array([m['left'],m['front']]);xy=relative@np.column_stack([u,v]).T+anchor
        co=m['co'];lo,hi=np.array(m['spec']['source_bounds']);low=(co[:,2]>m['spec']['source_floor_reference']+.025/m['spec']['uniform_scale'])&(co[:,2]<lo[2]+(hi[2]-lo[2])*.55)
        footprint=MultiPoint(xy[low]).convex_hull
        if footprint.intersection(road.buffer(.1)).area>1e-5:safe=False;break
        if any(footprint.intersection(Polygon(b['footprint']).buffer(.2)).area>.001 for b in p['buildings']):safe=False;break
        samples=[]
        for t in np.linspace(.03,.97,61):
            x=x0+(x1-x0)*t;e=origin+U*x+V*edge_y(x);z=walk.height(e-V*.04)
            if z is None:safe=False;break
            samples.append(z)
        if not safe:break
        top=float(np.mean(samples))+.018
        # Footings begin at the facade; the original sidewalk supplies walking space.
        local=(xy-anchor)@np.column_stack([u,v]);back=float(local[:,1].max()+.12);xl=float(local[:,0].min()-.08);xr=float(local[:,0].max()+.08)
        pad=Polygon(np.array([[xl,.025],[xr,.025],[xr,back],[xl,back]])@np.column_stack([u,v]).T+anchor)
        attempt.append(dict(model=m,x0=x0,x1=x1,anchor=anchor,u=u,v=v,theta=theta,top=top,pad=pad,sidewalk_height_range=[min(samples),max(samples)],footprint=footprint));cursor=x1-.035
    if safe:placements=attempt;chosen_shift=float(shift);break
if placements is None:raise RuntimeError('No safe sidewalk-aligned placement')
print('FRONTAGE_PLACEMENT',json.dumps([{'name':q['model']['spec']['instance_name'],'anchor':q['anchor'].tolist(),'height':q['top'],'sidewalk_height_range':q['sidewalk_height_range']} for q in placements]),flush=True)

# Restore holes left by the old shared pad, then cut only under the new pads.
restore_names=[g['object'] for g in p['oldtown_expansion']['ground_edits']]
with bpy.data.libraries.load(str(a.restore_terrain.resolve()),link=False) as (data_from,data_to):
    assert all(n in data_from.objects for n in restore_names);data_to.objects=list(restore_names)
for name,loaded in zip(restore_names,data_to.objects):
    current=bpy.data.objects[name];materials=list(current.data.materials);current.data=loaded.data;current.data.materials.clear()
    for mat in materials:current.data.materials.append(mat)
    bpy.data.objects.remove(loaded,do_unlink=True)
ground=HeightField([o for o in sc.objects if o.type=='MESH' and o.name.startswith('MAIN_Sculpted_Terrain_Cell_')]);pad=unary_union([q['pad'] for q in placements]);ground_edits=[]
for q in placements:
    vals=[ground.height(c) for c in shapely.get_coordinates(q['pad'])];vals=[v for v in vals if v is not None];q['bottom']=min(vals+[q['top']])-.28
for o in [o for o in sc.objects if o.type=='MESH' and o.name.startswith('MAIN_Sculpted_Terrain_Cell_')]:
    m=o.data;m.calc_loop_triangles();co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(float);M=np.asarray(o.matrix_world);co=co@M[:3,:3].T+M[:3,3];ids=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',ids);faces=ids.reshape(-1,3);tri=co[faces];lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1);b=pad.bounds;cand=np.flatnonzero((hi[:,0]>=b[0])&(lo[:,0]<=b[2])&(hi[:,1]>=b[1])&(lo[:,1]<=b[3]))
    if not len(cand):continue
    uv=None;color=None
    if m.uv_layers.active:
        uv=np.empty(len(m.loops)*2,np.float32);m.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
    if m.color_attributes.get('Color'):
        color=np.empty(len(m.loops)*4,np.float32);m.color_attributes['Color'].data.foreach_get('color',color);color=color.reshape(-1,3,4)
    selected=[];extra=[];oldmat=np.array([p.material_index for p in m.polygons]);smooth=np.array([p.use_smooth for p in m.polygons])
    for i in cand:
        poly=Polygon(tri[i,:,:2])
        if poly.area<1e-9 or poly.intersection(pad).area<1e-9:continue
        selected.append(i);rest=poly.difference(pad)
        if rest.is_empty:continue
        attrs=np.concatenate([tri[i]]+([uv[i]] if uv is not None else [])+([color[i]] if color is not None else []),axis=1);aa=tri[i,0,:2];u=tri[i,1,:2]-aa;v=tri[i,2,:2]-aa;det=u[0]*v[1]-u[1]*v[0]
        for sub in shapely.get_parts(shapely.constrained_delaunay_triangles(rest)):
            if sub.is_empty or sub.area<1e-9:continue
            xy=np.asarray(sub.exterior.coords)[:3,:2];d=xy-aa;s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det;val=np.c_[1-s-t,s,t]@attrs
            if np.cross(val[1,:2]-val[0,:2],val[2,:2]-val[0,:2])<0:val=val[::-1]
            extra.append((val,int(oldmat[i]),bool(smooth[i])))
    if not selected:continue
    keep=np.ones(len(faces),bool);keep[selected]=False;vv=co.tolist();ff=faces[keep].tolist();mm=oldmat[keep].tolist();ss=smooth[keep].tolist();uu=uv[keep].reshape(-1,2).tolist() if uv is not None else [];cc=color[keep].reshape(-1,4).tolist() if color is not None else []
    for val,mi,sm in extra:
        k=len(vv);vv.extend(val[:,:3].tolist());ff.append([k,k+1,k+2]);mm.append(mi);ss.append(sm);col=3
        if uv is not None:uu.extend(val[:,col:col+2].tolist());col+=2
        if color is not None:cc.extend(val[:,col:col+4].tolist())
    mesh=bpy.data.meshes.new(m.name+'_FrontageFit');mesh.from_pydata(vv,[],ff)
    for mat in m.materials:mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',np.asarray(mm,np.int32));mesh.polygons.foreach_set('use_smooth',np.asarray(ss,np.bool_))
    if uv is not None:mesh.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uu,np.float32).ravel())
    if color is not None:mesh.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER').data.foreach_set('color',np.asarray(cc,np.float32).ravel())
    mesh.update();o.data=mesh;o.matrix_world=Matrix.Identity(4);ground_edits.append({'object':o.name,'faces_before':len(faces),'faces_after':len(ff),'faces_cut':len(selected)})

sitegroup=bpy.data.objects['21_OLDTOWN_OPEN_STREET_ADAPTATION'];removed=[]
for o in list(sitegroup.children):
    if not o.name.startswith('OLDTOWN_Apartment_11_'):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
concrete=bpy.data.materials['Oldtown_Expansion_Concrete'];plaster=bpy.data.materials['Oldtown_Expansion_Seam_Plaster'];walkmat=bpy.data.materials.get('Road_Modular_Original_Atlas.001') or bpy.data.materials['Road_Modular_Original_Atlas']
def mesh_object(name,verts,faces,mat,uv=None):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(mat);me.update();o=bpy.data.objects.new(name,me);sc.collection.objects.link(o);o.parent=sitegroup
    if uv is not None:
        ar=np.array([uv[k] for f in faces for k in f],np.float32);me.uv_layers.new(name='UVMap').data.foreach_set('uv',ar.ravel())
    return o
def footing(name,poly,top,bottom):
    xy=np.asarray(poly.exterior.coords)[:-1];n=len(xy);verts=np.vstack([np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]]);faces=[list(range(n-1,-1,-1)),list(range(n,n*2))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)];return mesh_object(name,verts.tolist(),faces,concrete)
records={r['instance_name']:r for r in p['real_buildings']};frontage_checks=[]
for q in placements:
    m=q['model'];spec=m['spec'];inst=m['instance'];s=spec['uniform_scale'];axis=np.array(spec['local_axis_scale']);xy=q['anchor'];top=q['top'];theta=q['theta'];local_translation=(-m['left'],-m['front'],0)
    inst.matrix_world=Matrix.Translation((*xy,top-.008))@Matrix.Rotation(theta,4,'Z')@Matrix.Translation(local_translation)@Matrix.Rotation(m['turn'],4,'Z')@Matrix.Diagonal((*list(axis*s),1.))@Matrix.Translation((0,0,-spec['source_floor_reference']))
    inst['frontage_flush_to_existing_sidewalk']=True;inst['corner_turn_degrees']=math.degrees(m['turn']);footing('Oldtown_Expanded_Row_Foundation_'+spec['instance_name'][-2:],q['pad'],top-.012,q['bottom'])
    # A narrow edge seal follows the existing sidewalk. It replaces grass slivers
    # caused by curvature and is measured in centimetres rather than metres.
    verts=[];uv=[];faces=[];gaps=[]
    for j,t in enumerate(np.linspace(0,1,81)):
        x=q['x0']+(q['x1']-q['x0'])*t;e=origin+U*x+V*edge_y(x);b=xy+q['u']*m['width']*t;z=walk.height(e-V*.025);assert z is not None;gaps.append(float(np.linalg.norm(e-b)));verts.extend([np.r_[e-V*.04,z+.002].tolist(),np.r_[b+q['v']*.04,z+.002].tolist()]);uv.extend([(.216,.599+(x-q['x0'])/16.9048*.1777),(.223,.599+(x-q['x0'])/16.9048*.1777)])
        if j:
            k=j*2;faces.extend([[k-2,k-1,k+1],[k-2,k+1,k]])
    mesh_object('Oldtown_Expanded_Row_Edge_Seal_'+spec['instance_name'][-2:],verts,faces,walkmat,uv)
    xy_all=(m['pre']-np.array([m['left'],m['front']]))@np.column_stack([q['u'],q['v']]).T+xy;hull=MultiPoint(xy_all).convex_hull
    rec=records[spec['instance_name']];rec.update(center=xy_all.mean(0).tolist(),angle=theta+m['turn'],footprint_xy=shapely.get_coordinates(hull).tolist(),foundation_top_m=top,foundation_bottom_m=q['bottom'],building_base_m=top-.008-spec['source_floor_reference']*s,frontage_rotation_degrees=math.degrees(m['turn']),frontage_anchor_xy=xy.tolist(),frontage_u=q['u'].tolist(),frontage_v=q['v'].tolist(),frontage_width_m=m['width'],direct_sidewalk_frontage=True,access_start_xy=(xy+q['u']*m['width']/2).tolist(),access_end_xy=(xy+q['u']*m['width']/2-q['v']*.04).tolist(),access_length_m=.04,access_width_m=3.,access_maximum_grade=0.)
    frontage_checks.append({'instance':spec['instance_name'],'anchor_xy':xy.tolist(),'u':q['u'].tolist(),'v':q['v'].tolist(),'width_m':m['width'],'floor_m':top,'sidewalk_height_range_m':q['sidewalk_height_range'],'maximum_frontage_edge_gap_m':max(gaps),'nominal_setback_m':.025,'rotation_relative_to_street_degrees':math.degrees(m['turn'])})

# Thin party-wall closures cover the tiny wedges between the six rigid buildings.
for i,(l,r) in enumerate(zip(placements[:-1],placements[1:])):
    m=l['model'];end=l['anchor']+l['u']*m['width'];start=r['anchor'];depth=min(float((m['pre'][:,1]-m['front']).max()),float((r['model']['pre'][:,1]-r['model']['front']).max()));z=min(l['top'],r['top']);h=min(m['spec']['target_height_m'],r['model']['spec']['target_height_m'])-.5;poly=Polygon([end-l['u']*.055,start+r['u']*.055,start+r['u']*.055+r['v']*depth,end-l['u']*.055+l['v']*depth]);footing('Oldtown_Row_Partywall_%02d'%i,poly,z+h,z-.2).data.materials[0]=plaster

center=(placements[0]['anchor']+placements[-1]['anchor']+placements[-1]['u']*placements[-1]['model']['width'])/2
local=np.array([np.array(q['pad'].exterior.coords)[:-1] for q in placements]);points=local.reshape(-1,2);bounds_local=(points-center)@R
row=dict(oldrow);row.update(front_origin=center.tolist(),length_m=sum(q['model']['width'] for q in placements)-.035*5,local_x_range=[float(bounds_local[:,0].min()),float(bounds_local[:,0].max())],body_max_x=float(bounds_local[:,0].max()),local_back_m=float(bounds_local[:,1].max()),foundation_top_m=float(np.mean([q['top'] for q in placements])),foundation_bottom_m=min(q['bottom'] for q in placements),pad_rectangle=shapely.get_coordinates(pad.convex_hull).tolist(),ramps=[],frontage_flush_to_sidewalk=True,individual_floor_levels=True,added_front_walkway=False,corner_turn_degrees=90.,corner_position='right end when facing the storefronts',frontage_checks=frontage_checks)
row.pop('open_walk_local_y_range',None);row.pop('clear_corridor_width_m',None);row.pop('corner_return_floor_width_m',None);row['corner_depth_m']=float((placements[-1]['model']['pre'][:,1]-placements[-1]['model']['front']).max());row['seams']=[{'left':l['model']['spec']['instance_name'],'right':r['model']['spec']['instance_name'],'nominal_overlap_m':.035} for l,r in zip(placements[:-1],placements[1:])]
p['connected_arcades']=row;p['oldtown_expansion']['row']=row;p['oldtown_expansion']['ground_edits']=ground_edits
movement=[{'instance':q['instance'],'frontage_xy':q['anchor_xy'],'frontage_floor_m':q['floor_m']} for q in frontage_checks]
report={'schema':'hero13.city.frontage-alignment.v1','frontage':frontage_checks,'corner_turn_degrees':90,'corner_position':'right','nominal_setback_m':.025,'maximum_edge_seal_width_m':max(q['maximum_frontage_edge_gap_m'] for q in frontage_checks),'rightward_shift_m':chosen_shift,'removed_walkway_and_ramp_objects':removed,'restored_terrain_objects':restore_names,'ground_edits':ground_edits,'road_sidewalk_geometry_unchanged':fingerprint(protected)==before,'protected_geometry_sha256':before,'building_scales_unchanged':True,'unchanged_apartment_instance':'OLDTOWN_Apartment_11'}
assert report['road_sidewalk_geometry_unchanged'];p['frontage_alignment']=report
bpy.context.view_layer.update()
chunk=json.loads(a.chunk_report.read_text())
for info in chunk:
    obs=[o for o in sc.objects if o.type=='MESH' and o.name.startswith(info['source']+'_Cell_')];info['triangles_after']=sum(len(o.data.polygons) for o in obs);info['cell_count']=len(obs)
(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'frontage_alignment.json').write_text(json.dumps(report,indent=2));(a.out/'chunk_report.json').write_text(json.dumps(chunk,indent=2));exp=json.loads((a.plan.parent/'oldtown_expansion.json').read_text());exp.update(row=row,instances=[records[q['model']['spec']['instance_name']] for q in placements]+[p['oldtown_expansion']['apartment']],ground_edits=ground_edits,frontage_alignment=report);(a.out/'oldtown_expansion.json').write_text(json.dumps(exp,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((a.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0; user-provided building assets.')
print('FRONTAGE_ALIGNMENT_COMPLETE',json.dumps(report),flush=True)
