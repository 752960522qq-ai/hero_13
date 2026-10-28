"""Plan a six-asset street frontage, an enlarged corner shop and an apartment."""
from pathlib import Path
import argparse,gzip,json,math,sys
import bpy,numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--scheme',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union,nearest_points
sys.path.insert(0,str(Path(__file__).resolve().parent));from city_surface_sampling import HeightField
models=[]
spec=[('old+building+facade+6.glb',11.8,1.,'OLDTOWN_Connected_Arcade_06'),('storefront+building+7.glb',11.5,1.,'OLDTOWN_Connected_Arcade_07'),('urban+building+facade+5.glb',11.8,1.,'OLDTOWN_Connected_Arcade_05'),('old+urban+building+8.glb',15.2,1.,'OLDTOWN_Connected_Shop_08'),('city+street+building+9.glb',14.4,1.,'OLDTOWN_Connected_Shop_09'),('urban+building+facade+10.glb',11.8,1.45,'OLDTOWN_Corner_Shop_10'),('apartment+building+11.glb',14.2,1.,'OLDTOWN_Apartment_11')]
for file,height,depth,name in spec:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str((a.models/file).resolve()));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];q=[];tris=[]
    for o in obs:
        vv=np.array([o.matrix_world@v.co for v in o.data.vertices]);q.append(vv);o.data.calc_loop_triangles();tris.append(vv[np.array([t.vertices[:] for t in o.data.loop_triangles])])
    q=np.concatenate(q);tri=np.concatenate(tris);lo=q.min(0);hi=q.max(0);dims=hi-lo;s=height/dims[2];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(normal,axis=1)/2;z=tri[:,:,2].mean(1);sel=(z<lo[2]+dims[2]*.065)&(normal[:,2]>np.linalg.norm(normal,axis=1)*.7);levels=z[sel];weights=area[sel]
    hist,edges=np.histogram(levels,bins=100,range=(lo[2],lo[2]+dims[2]*.065),weights=weights);k=int(np.argmax(hist));sel=(levels>=edges[max(0,k-1)])&(levels<=edges[min(len(edges)-1,k+2)]);floor=float(np.average(levels[sel],weights=weights[sel]))
    core=q[(q[:,2]>lo[2]+dims[2]*.17)&(q[:,2]<lo[2]+dims[2]*.75)&(q[:,1]>lo[1]+dims[1]*.35)&(q[:,1]<lo[1]+dims[1]*.8)];left,right=np.quantile(core[:,0],[.005,.995]);front=float(np.quantile(q[(q[:,2]>lo[2]+dims[2]*.12)&(q[:,2]<lo[2]+dims[2]*.7),1],.01))
    models.append({'file':file,'instance_name':name,'target_height_m':height,'source_bounds':[lo.tolist(),hi.tolist()],'source_dimensions':dims.tolist(),'source_floor_reference':floor,'source_front_reference':front,'source_core_left':float(left),'source_core_right':float(right),'uniform_scale':s,'local_axis_scale':[1.,depth,1.]})
rowmodels=models[:6];cursor=0
for m in rowmodels:m['local_x_translation']=cursor-m['source_core_left']*m['uniform_scale'];cursor+=(m['source_core_right']-m['source_core_left'])*m['uniform_scale']-.04
length=cursor+.04
for m in rowmodels:m['local_x_translation']-=length/2
xmin=min(m['source_bounds'][0][0]*m['uniform_scale']+m['local_x_translation'] for m in rowmodels)-.15
bodymax=max(m['source_bounds'][1][0]*m['uniform_scale']+m['local_x_translation'] for m in rowmodels);xmax=bodymax+2.2
back=max((m['source_bounds'][1][1]-m['source_front_reference'])*m['uniform_scale']*m['local_axis_scale'][1] for m in rowmodels)+.25
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();p=json.loads(a.plan.read_text());scheme=json.loads(gzip.decompress(a.scheme.read_bytes()));road=shapely.from_geojson(scheme['new_pavement']);full=shapely.from_geojson(scheme['new_full_footprint']);blocked=full.buffer(.15);walkshape=full.difference(road).buffer(-.18)
oldnames=set(p['connected_arcades']['instances']);oldreal=[b for b in p['real_buildings'] if b['instance_name'] not in oldnames];polys=[Polygon(b['footprint']) for b in p['buildings']];tree=shapely.STRtree(polys)
protected=unary_union([Polygon(b['footprint_xy']).buffer(1.1) for b in oldreal]+[LineString([b['access_start_xy'],b['access_end_xy']]).buffer(2.2) for b in oldreal]);coast=Polygon(p['coasts']['MAIN']).buffer(-12)
terrain=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('MAIN_Sculpted_Terrain_Cell_','Junction_Repairs_Ground_Infill'))]);walk=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('MAIN_Sidewalk_Modular_Continuous_Cell_','Sidewalk_Continuous_Transition_Base_Cell_','Junction_Repairs_Sidewalk_OriginalAtlas_Cell_'))])
tt=terrain.tri;tl=tt[:,:,:2].min(1);th=tt[:,:,:2].max(1)
def extrema(rect):
    rect=np.asarray(rect);poly=Polygon(rect);lo=rect.min(0);hi=rect.max(0);vals=[]
    for t in tt[np.all(th>=lo,1)&np.all(tl<=hi,1)]:
        xy=shapely.get_coordinates(Polygon(t[:,:2]).intersection(poly))
        if not len(xy):continue
        aa=t[0,:2];u=t[1,:2]-aa;v=t[2,:2]-aa;d=xy-aa;det=u[0]*v[1]-u[1]*v[0];s=(d[:,0]*v[1]-d[:,1]*v[0])/det;r=(u[0]*d[:,1]-u[1]*d[:,0])/det;vals.extend((t[0,2]+s*(t[1,2]-t[0,2])+r*(t[2,2]-t[0,2])).tolist())
    if not vals:raise ValueError('no terrain')
    return min(vals),max(vals)
def profile(start,end,top,pad,width=2.):
    start=np.asarray(start);end=np.asarray(end);u=end-start;L=float(np.linalg.norm(u));u/=L;n=np.array([-u[1],u[0]]);off=np.linspace(-width/2,width/2,7);endxy=end[None,:]+off[:,None]*n;endz=np.array([walk.height(x) for x in endxy],float)
    if not np.isfinite(endz).all():raise ValueError('missing sidewalk')
    stations=np.linspace(0,L,int(math.ceil(L/.4))+1);xy=start[None,None,:]+stations[:,None,None]*u[None,None,:]+off[None,:,None]*n[None,None,:];g=np.array([[(top-.021) if pad.covers(Point(x)) else (terrain.height(x) if terrain.height(x) is not None else np.nan) for x in row] for row in xy]);cross=stations[:,None]/L*(endz-endz.mean())[None,:];h=np.interp(stations,[0,L],[top+.004,float(endz.mean())+.006]);h=np.maximum(h,np.max(np.where(np.isfinite(g),g-cross+.025,-1e6),axis=1))
    for k in range(1,len(h)):h[k]=max(h[k],h[k-1]-.078*(stations[k]-stations[k-1]))
    for k in range(len(h)-2,-1,-1):h[k]=max(h[k],h[k+1]-.078*(stations[k+1]-stations[k]))
    z=h[:,None]+cross;grade=float(np.max(np.abs(np.diff(z,axis=0))/np.diff(stations)[:,None]))
    if abs(h[0]-top-.004)>.012 or abs(h[-1]-endz.mean()-.006)>.012 or grade>.084:raise ValueError('ramp too short')
    return {'start_xy':start.tolist(),'end_xy':end.tolist(),'length_m':L,'width_m':width,'maximum_grade':grade,'end_max_lip_m':float(np.max(abs(z[-1]-endz))),'xy':xy.tolist(),'z':z.tolist(),'ground_floor':float(min(top-.25,np.nanmin(g) if np.isfinite(g).any() else top-.25))-.2}
def hit_placeholders(poly,limit=9):
    hits=[int(i) for i in tree.query(poly.buffer(.7),predicate='intersects')]
    if len(hits)>limit or any(p['buildings'][i]['zone']!='OLDTOWN' for i in hits):return None
    return hits
candidates=[]
for eid,e in enumerate(p['edges']):
    if e['name'] not in ['M18_Oldtown_North','M19_Oldtown_South'] or e['length']<length+25:continue
    for reverse in [False,True]:
        q=np.array(e['points']);q=q[::-1] if reverse else q;node=e['a'] if reverse else e['b']
        if len(p['nodes'][node]['edges'])<3:continue
        ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))];line=LineString(q[:,:2])
        for setback in [12.,14.,16.,18.,20.]:
            along=ds[-1]-setback-length/2
            if along<length/2+15:continue
            center=np.array([np.interp(along,ds,q[:,i]) for i in range(2)]);p0=np.array([np.interp(along-length/2,ds,q[:,i]) for i in range(2)]);p1=np.array([np.interp(along+length/2,ds,q[:,i]) for i in range(2)]);u=p1-p0;u/=np.linalg.norm(u);v=np.array([-u[1],u[0]]);rot=np.column_stack([u,v]);dev=max(line.distance(Point(center+u*d)) for d in np.linspace(-length/2,length/2,17))
            if dev>.8:continue
            for gap in [6.,7.5,9.]:
                origin=center+v*(e['carriage_width']/2+3+gap);rect=np.array([[xmin,-3.45],[xmax,-3.45],[xmax,back],[xmin,back]])@rot.T+origin;poly=Polygon(rect)
                if not coast.covers(poly) or poly.intersects(blocked) or poly.intersects(protected):continue
                hits=hit_placeholders(poly)
                if hits is None:continue
                starts=[];ends=[];safe=True
                for x in [xmin+5.,0.,bodymax-3.5]:
                    start=origin+u*x-v*3.1;end=center+u*x+v*(e['carriage_width']/2+1.6);g=LineString([start,end]).buffer(1.1,cap_style='flat')
                    if g.intersects(road) or g.intersects(protected) or any(int(i) not in hits for i in tree.query(g,predicate='intersects')):safe=False;break
                    starts.append(start);ends.append(end)
                if not safe:continue
                corner_depth=(rowmodels[-1]['source_bounds'][1][1]-rowmodels[-1]['source_front_reference'])*rowmodels[-1]['uniform_scale']*1.45
                start=origin+u*(bodymax+1.8)+v*(corner_depth*.55);target=nearest_points(Point(start),walkshape)[1];end=np.array(target.coords[0]);g=LineString([start,end]).buffer(.8,cap_style='flat')
                if g.intersects(road) or g.intersects(protected) or any(int(i) not in hits for i in tree.query(g,predicate='intersects')):continue
                starts.append(start);ends.append(end);score=np.linalg.norm(center-np.array([-60.,302.]))*.06+len(hits)*3+dev*8+(gap-6)*.5
                candidates.append({'edge_index':eid,'road':e['name'],'junction_node':node,'front_origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'pad_rectangle':rect.tolist(),'hits':hits,'starts':[s.tolist() for s in starts],'ends':[s.tolist() for s in ends],'score':float(score),'corner_depth_m':float(corner_depth)})
candidates.sort(key=lambda q:q['score']);print('EXPANSION_CANDIDATES',len(candidates),'row length',length,flush=True);chosen=None
for c in candidates:
    poly=Polygon(c['pad_rectangle'])
    try:
        lo,hi=extrema(c['pad_rectangle']);endlevels=[walk.height(e) for e in c['ends']]
        if any(z is None for z in endlevels):continue
        top=max(endlevels)+.07
        if hi-top>.85 or top-lo>1.2:continue
        ramps=[profile(s,e,top,poly,1.6 if i==3 else 2.) for i,(s,e) in enumerate(zip(c['starts'],c['ends']))]
        c.update(terrain_min_m=lo,terrain_max_m=hi,foundation_top_m=top,foundation_bottom_m=min(lo,top)-.25,site_cut_max_depth_m=max(0,hi-top),ramps=ramps,removed_placeholders=[p['buildings'][i]['name'] for i in c['hits']]);chosen=c;break
    except ValueError:continue
if chosen is None:raise RuntimeError('No safe six-building corner frontage found')
print('EXPANSION_ROW_SITE',json.dumps({k:v for k,v in chosen.items() if k not in ['ramps','hits','starts','ends']}),flush=True)
# Apartment lot remains separate from the corner frontage, close to the older
# apartment cluster, with an independent sidewalk approach.
rowpoly=Polygon(chosen['pad_rectangle']);removed=set(chosen['removed_placeholders']);m=models[-1];s=m['uniform_scale'];lo,hi=np.array(m['source_bounds']);w=(hi[0]-lo[0])*s+1.2;d=(hi[1]-m['source_front_reference'])*s+.65;aptc=[]
for eid,e in enumerate(p['edges']):
    if e['name'] not in ['M18_Oldtown_North','M19_Oldtown_South'] or e['length']<w+35:continue
    q=np.array(e['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
    for along in np.arange(w/2+19,ds[-1]-w/2-19,9):
        center=np.array([np.interp(along,ds,q[:,i]) for i in range(2)]);aa=np.array([np.interp(along-1,ds,q[:,i]) for i in range(2)]);bb=np.array([np.interp(along+1,ds,q[:,i]) for i in range(2)]);t=bb-aa;t/=np.linalg.norm(t)
        for side in [-1,1]:
            u=t*side;v=np.array([-u[1],u[0]]);origin=center+v*(e['carriage_width']/2+3+8);rot=np.column_stack([u,v]);rect=np.array([[-w/2,-.8],[w/2,-.8],[w/2,d],[-w/2,d]])@rot.T+origin;poly=Polygon(rect)
            if not coast.covers(poly) or poly.intersects(blocked) or poly.intersects(protected) or poly.distance(rowpoly)<2:continue
            hits=hit_placeholders(poly,5)
            if hits is None:continue
            start=origin-v*.55;end=center+v*(e['carriage_width']/2+1.6);g=LineString([start,end]).buffer(1.6,cap_style='flat')
            if g.intersects(road) or g.intersects(protected) or g.intersects(rowpoly) or any(int(i) not in hits and p['buildings'][int(i)]['name'] not in removed for i in tree.query(g,predicate='intersects')):continue
            aptc.append((float(np.linalg.norm(origin-np.array([-20.,255.]))+len(hits)*8),{'road':e['name'],'front_origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'pad_rectangle':rect.tolist(),'start':start.tolist(),'end':end.tolist(),'hits':hits}))
aptc.sort(key=lambda x:x[0]);aptsite=None
for _,c in aptc:
    try:
        lo,hi=extrema(c['pad_rectangle'])
        if hi-lo>1.1:continue
        top=hi+.07;r=profile(c['start'],c['end'],top,Polygon(c['pad_rectangle']),3.)
        c.update(terrain_min_m=lo,terrain_max_m=hi,foundation_top_m=top,foundation_bottom_m=lo-.25,ramps=[r],removed_placeholders=[p['buildings'][i]['name'] for i in c['hits']]);aptsite=c;break
    except ValueError:continue
if aptsite is None:raise RuntimeError('No suitable apartment lot')
print('EXPANSION_APARTMENT_SITE',json.dumps({k:v for k,v in aptsite.items() if k not in ['ramps','hits']}),flush=True)
for c in [chosen,aptsite]:
    for k in ['hits','starts','ends','start','end']:c.pop(k,None)
result={'models':models,'row_length_m':length,'row_local_x_range':[xmin,xmax],'row_body_max_x':bodymax,'row_local_back_m':back,'row_site':chosen,'apartment_site':aptsite,'corner_model':'urban+building+facade+10.glb','corner_depth_scale':1.45,'removed_added_canopy':True}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2))
