"""Fit three source shop-house assets into one continuous old-town frontage."""
from pathlib import Path
import argparse,gzip,json,math,sys
import bpy,numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent));from city_surface_sampling import HeightField
models=[]
for file,height,name in [('old+building+facade+6.glb',11.8,'OLDTOWN_Connected_Arcade_06'),('storefront+building+7.glb',11.5,'OLDTOWN_Connected_Arcade_07'),('urban+building+facade+5.glb',11.8,'OLDTOWN_Connected_Arcade_05')]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str((a.models/file).resolve()));bpy.context.view_layer.update()
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH'];verts=[];tri=[]
    for o in objs:
        q=np.array([o.matrix_world@v.co for v in o.data.vertices]);verts.append(q);o.data.calc_loop_triangles();tri.append(q[np.array([t.vertices[:] for t in o.data.loop_triangles])])
    q=np.concatenate(verts);tri=np.concatenate(tri);lo=q.min(0);hi=q.max(0);dims=hi-lo;scale=height/dims[2]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(normals,axis=1)/2;zz=tri[:,:,2].mean(1)
    mask=(zz<lo[2]+dims[2]*.065)&(normals[:,2]>np.linalg.norm(normals,axis=1)*.7)
    weights=area[mask];levels=zz[mask];assert len(levels)
    hist,edges=np.histogram(levels,bins=100,range=(lo[2],lo[2]+dims[2]*.065),weights=weights)
    k=int(np.argmax(hist));select=(levels>=edges[max(0,k-1)])&(levels<=edges[min(len(edges)-1,k+2)])
    floor=float(np.average(levels[select],weights=weights[select]))
    core=q[(q[:,2]>lo[2]+dims[2]*.17)&(q[:,2]<lo[2]+dims[2]*.75)&(q[:,1]>lo[1]+dims[1]*.35)&(q[:,1]<lo[1]+dims[1]*.8)]
    left,right=np.quantile(core[:,0],[.005,.995]);front=float(np.quantile(q[(q[:,2]>lo[2]+dims[2]*.12)&(q[:,2]<lo[2]+dims[2]*.7),1],.01))
    rec={'file':file,'instance_name':name,'target_height_m':height,'source_bounds':[lo.tolist(),hi.tolist()],'source_floor_reference':floor,'source_core_left':float(left),'source_core_right':float(right),'source_front_reference':front,'uniform_scale':scale,'source_dimensions':dims.tolist()}
    models.append(rec);print('ARCADE_SOURCE',json.dumps(rec),flush=True)
# Shared party walls touch with a 4 cm overlap; roof and original plinth
# overhangs may overlap only inside the shared seam.
cursor=0
for r in models:
    r['local_x_translation']=cursor-r['source_core_left']*r['uniform_scale'];cursor+=(r['source_core_right']-r['source_core_left'])*r['uniform_scale']-.04
length=cursor+.04
for r in models:r['local_x_translation']-=length/2
xmin=min(r['source_bounds'][0][0]*r['uniform_scale']+r['local_x_translation'] for r in models)-.15
xmax=max(r['source_bounds'][1][0]*r['uniform_scale']+r['local_x_translation'] for r in models)+.15
back=max((r['source_bounds'][1][1]-r['source_front_reference'])*r['uniform_scale'] for r in models)+.25
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();plan=json.loads(a.plan.read_text())
raw=a.scheme.read_bytes();scheme=json.loads(gzip.decompress(raw) if a.scheme.suffix=='.gz' else raw)
road=shapely.from_geojson(scheme['new_pavement']);full=shapely.from_geojson(scheme['new_full_footprint']);fullbuffer=full.buffer(.25)
buildings=plan['buildings'];polys=[Polygon(b['footprint']) for b in buildings];tree=shapely.STRtree(polys)
protected=unary_union([Polygon(b['footprint_xy']).buffer(3) for b in plan['real_buildings']]+[LineString([b['access_start_xy'],b['access_end_xy']]).buffer(b.get('access_width_m',3)/2+2) for b in plan['real_buildings']])
coast=Polygon(plan['coasts']['MAIN']).buffer(-15);candidates=[]
for eid,e in enumerate(plan['edges']):
    if e['name'] not in ['M18_Oldtown_North','M19_Oldtown_South'] or e['length']<length+42:continue
    q=np.array(e['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))];line=LineString(q[:,:2])
    for along in np.arange(length/2+21,ds[-1]-length/2-21,8):
        center=np.array([np.interp(along,ds,q[:,i]) for i in range(2)]);p0=np.array([np.interp(along-length/2,ds,q[:,i]) for i in range(2)]);p1=np.array([np.interp(along+length/2,ds,q[:,i]) for i in range(2)])
        tangent=p1-p0;tangent/=np.linalg.norm(tangent);n=np.array([-tangent[1],tangent[0]])
        deviation=max(line.distance(Point(center+tangent*d)) for d in np.linspace(-length/2,length/2,13))
        if deviation>.6:continue
        for side in [-1,1]:
            u=tangent*side;v=n*side;rot=np.column_stack([u,v]);front=center+v*(e['carriage_width']/2+3+6)
            local=np.array([[xmin,-3.45],[xmax,-3.45],[xmax,back],[xmin,back]]);rect=local@rot.T+front;poly=Polygon(rect)
            if not coast.covers(poly) or poly.intersects(fullbuffer) or poly.intersects(protected):continue
            hits=[int(i) for i in tree.query(poly.buffer(1.2),predicate='intersects')]
            if len(hits)>5 or any(buildings[i]['zone']!='OLDTOWN' for i in hits):continue
            ends=[];bad=False
            for x in [xmin+4,0,xmax-4]:
                start=front+u*x-v*3.1;end=center+u*x+v*(e['carriage_width']/2+1.6);g=LineString([start,end]).buffer(1.05,cap_style='flat')
                if g.intersects(road) or g.intersects(protected) or any(int(i) not in hits for i in tree.query(g.buffer(.6),predicate='intersects')):bad=True;break
                ends.append((start.tolist(),end.tolist()))
            if bad:continue
            zrange=np.ptp([np.interp(along+d,ds,q[:,2]) for d in np.linspace(-length/2,length/2,11)])
            score=np.linalg.norm(center-np.array([-130,310]))*.06+zrange*45+len(hits)*4+deviation*10
            candidates.append({'edge_index':eid,'road':e['name'],'road_center':center.tolist(),'front_origin':front.tolist(),'u':u.tolist(),'v':v.tolist(),'pad_rectangle':rect.tolist(),'remove_indices':hits,'ramps':ends,'score':float(score),'road_height_range_m':float(zrange),'road_curvature_deviation_m':float(deviation)})
candidates.sort(key=lambda q:q['score']);print('ARCADE_SITE_CANDIDATES',len(candidates),flush=True)
landobjs=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('MAIN_Sculpted_Terrain_Cell_') or o.name=='Junction_Repairs_Ground_Infill')]
walkobjs=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith(('MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_')))]
terrain=HeightField(landobjs);walkfield=HeightField(walkobjs);t=terrain.tri;tri_lo=t[:,:,:2].min(1);tri_hi=t[:,:,:2].max(1)
def extrema(rect):
    b=np.array(rect);lo=b.min(0);hi=b.max(0);select=np.all(tri_hi>=lo,1)&np.all(tri_lo<=hi,1);out=[]
    for tri in t[select]:
        xy=shapely.get_coordinates(Polygon(tri[:,:2]).intersection(Polygon(rect)))
        if not len(xy):continue
        aa=tri[0,:2];u=tri[1,:2]-aa;v=tri[2,:2]-aa;d=xy-aa;det=u[0]*v[1]-u[1]*v[0];s=(d[:,0]*v[1]-d[:,1]*v[0])/det;r=(u[0]*d[:,1]-u[1]*d[:,0])/det
        out.extend((tri[0,2]+s*(tri[1,2]-tri[0,2])+r*(tri[2,2]-tri[0,2])).tolist())
    return min(out),max(out)
chosen=None;failures=[]
for c in candidates[:140]:
    lo,hi=extrema(c['pad_rectangle']);top=hi+.07
    if hi-lo>1.1:continue
    profiles=[]
    try:
        for start,end in c['ramps']:
            start=np.array(start);end=np.array(end);delta=end-start;L=np.linalg.norm(delta);u=delta/L;n=np.array([-u[1],u[0]]);offsets=np.linspace(-1,1,5)
            endxy=end[None,:]+offsets[:,None]*n;endz=np.array([walkfield.height(x) for x in endxy],float)
            if not np.isfinite(endz).all():raise ValueError('missing sidewalk')
            ds=np.linspace(0,L,int(math.ceil(L/.4))+1);xy=start[None,None,:]+ds[:,None,None]*u[None,None,:]+offsets[None,:,None]*n[None,None,:];cross=ds[:,None]/L*(endz-endz.mean())[None,:]
            ground=np.array([[terrain.height(p) if terrain.height(p) is not None else np.nan for p in row] for row in xy]);z=np.interp(ds,[0,L],[top+.004,float(endz.mean())+.006]);required=np.max(np.where(np.isfinite(ground),ground-cross+.025,-1e6),axis=1);z=np.maximum(z,required)
            for i in range(1,len(z)):z[i]=max(z[i],z[i-1]-.08*(ds[i]-ds[i-1]))
            for i in range(len(z)-2,-1,-1):z[i]=max(z[i],z[i+1]-.08*(ds[i+1]-ds[i]))
            zz=z[:,None]+cross;grade=float(np.max(np.abs(np.diff(zz,axis=0))/np.diff(ds)[:,None]))
            if abs(z[0]-top-.004)>.012 or abs(z[-1]-endz.mean()-.006)>.012 or grade>.085:raise ValueError('approach too short')
            profiles.append({'start_xy':start.tolist(),'end_xy':end.tolist(),'length_m':float(L),'maximum_grade':grade,'end_max_lip_m':float(np.max(abs(zz[-1]-endz))),'xy':xy.tolist(),'z':zz.tolist(),'ground_floor':float(np.nanmin(ground))-.2})
        c.update(terrain_min_m=lo,terrain_max_m=hi,foundation_top_m=top,foundation_bottom_m=lo-.25,ramp_profiles=profiles);chosen=c;break
    except ValueError as err:failures.append(str(err))
if chosen is None:raise RuntimeError('No connected arcade site fits the terrain: '+str(failures[:8]))
chosen['removed_placeholders']=[buildings[i]['name'] for i in chosen.pop('remove_indices')]
result={'models':models,'row_length_m':length,'local_x_range':[xmin,xmax],'local_back_m':back,'site':chosen,'continuous_clear_corridor_width_m':2.6,'canopy_underside_height_m':3.8,'source_asset_instances':3}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2));print('ARCADE_PLAN_CHOSEN',json.dumps({k:v for k,v in chosen.items() if k!='ramp_profiles'}),flush=True)
