"""Rebuild a three-island city from metric coast controls and a layered road graph."""
import argparse,json,math,collections,heapq
from pathlib import Path
from compact_city_math import *
from shapely.ops import nearest_points,substring
from shapely.geometry import box,MultiPoint

def parts(g,kind):return [q for q in shapely.get_parts(g) if q.geom_type==kind and not q.is_empty]

def main(a):
    islands,lake=coasts();land=unary_union(list(islands.values())).difference(lake)
    rings={k:p.buffer(-95 if k=='MAIN' else -72) for k,p in islands.items()}
    domains={k:(p.difference(lake.buffer(44)) if k=='WEST' else p) for k,p in rings.items()}
    routes=[]
    def height(xy):return raw_height(xy,islands,lake)
    def add(name,line,region='MAIN',carriage=9,walk=2,layer='GROUND_MAIN',zfn=None,bridge=False,clip=True):
        if clip:line=line.intersection(domains[region])
        for q in parts(line,'LineString'):
            if q.length<8:continue
            routes.append(dict(name=name,line=q,region=region,carriage_width=carriage,sidewalk_width=walk,width=carriage+2*walk,layer=layer,bridge=bridge,zfn=zfn or height))
    for k,p in rings.items():add(k+'_COASTAL_RING',LineString(p.exterior.coords),k,15,2.5,'GROUND_'+k,clip=False)
    add('WEST_LAKE_CIRCUIT',LineString(lake.buffer(44).exterior.coords),'WEST',7,2,'GROUND_WEST',clip=False)
    # Fine old-city blocks; larger civic/CBD and industrial blocks surround them.
    main_x=[-980,-790,-640,-520,-410,-290,-160,-50,80,190,350,470,590,730,860,1090,1280]
    for x in main_x:
        lo=-200 if x not in [-980,-790,1090,1280] else 80
        hi=1600 if x in [-790,-410,-160,80,350,590,860,1090] else 650
        if x==730:hi=410
        carriage=15 if x in [-410,80,860] else 9 if x in [-790,350,590,1090] else 6
        name=f'MAIN_NS_{x}'
        if x==860:
            def iz(xy):
                p=np.asarray(xy).reshape(-1,2);d=np.abs(p[:,1]-650);return height(p)+9.0*(1-smoothstep((d-42)/195))
            add(name,LineString([(x,lo),(x,hi)]),carriage=15,walk=2.5,layer='IX_B_UPPER',zfn=iz)
        else:add(name,LineString([(x,lo),(x,hi)]),carriage=carriage,walk=2.5 if carriage>=15 else 2,layer='GROUND_MAIN')
    for y in [120,230,320,410,520,650,950,1200,1400]:
        line=LineString([(-1500,y),(1600,y)])
        if y==520:line=line.intersection(box(-1500,-1000,590,1800))
        carriage=15 if y in [650,950,1200] else 9 if y in [230,410,520] else 6
        if y==950:
            def iz(xy):
                p=np.asarray(xy).reshape(-1,2);d=np.abs(p[:,0]-80);return height(p)+8*(1-smoothstep((d-45)/200))
            add('MAIN_EW_950',line,carriage=15,walk=2.5,layer='IX_A_UPPER',zfn=iz)
        else:add(f'MAIN_EW_{y}',line,carriage=carriage,walk=3 if y in [230,410] else 2.5 if carriage>=15 else 2,layer='GROUND_MAIN')
    for x in [-1530,-1310,-1060,-800,-570]:add(f'WEST_NS_{x}',LineString([(x,-1750),(x,-300)]),'WEST',9,2,'GROUND_WEST')
    for y in [-580,-780,-1100,-1330,-1480]:add(f'WEST_EW_{y}',LineString([(-1850,y),(-300,y)]),'WEST',9 if y!=-1100 else 15,2,'GROUND_WEST')
    for x in [500,750,1000,1250,1460]:add(f'EAST_NS_{x}',LineString([(x,-1800),(x,-350)]),'EAST',9 if x!=1000 else 15,2,'GROUND_EAST')
    for y in [-650,-850,-1080,-1320,-1500]:add(f'EAST_EW_{y}',LineString([(150,y),(1800,y)]),'EAST',9 if y!=-1080 else 15,2,'GROUND_EAST')
    # Diamond ramps are genuine graph links between upper and lower roads.
    for sx in [-1,1]:
        for sy in [-1,1]:
            cp=[(80+sx*90,950),(80+sx*157,950+sy*28),(80+sx*117,950+sy*126),(80,950+sy*180)]
            q=LineString(curve(cp,False,3));L=q.length;z0=float(height([cp[0]])[0]+8*(1-smoothstep((90-45)/200)));z1=float(height([cp[-1]])[0])
            def rampz(xy,q=q,L=L,z0=z0,z1=z1):return z0+(z1-z0)*smoothstep(np.array([q.project(Point(p))/L for p in np.asarray(xy).reshape(-1,2)]))
            add(f'IX_A_RAMP_{sx}_{sy}',q,carriage=7,walk=1.5,layer=f'IX_A_RAMP_{sx}_{sy}',zfn=rampz,clip=False)
    for sy,sx in [(-1,-1),(1,1)]:
        cp=[(860,650+sy*85),(860+sx*30,650+sy*148),(860+sx*126,650+sy*112),(860+sx*180,650)]
        q=LineString(curve(cp,False,3));L=q.length;z0=float(height([cp[0]])[0]+9.0*(1-smoothstep((85-42)/195)));z1=float(height([cp[-1]])[0])
        def rampz(xy,q=q,L=L,z0=z0,z1=z1):return z0+(z1-z0)*smoothstep(np.array([q.project(Point(p))/L for p in np.asarray(xy).reshape(-1,2)]))
        add(f'IX_B_RAMP_{sy}',q,carriage=7,walk=1.5,layer=f'IX_B_RAMP_{sy}',zfn=rampz,clip=False)
    def ringpoint(k,xy):return np.array(nearest_points(Point(xy),rings[k].exterior)[1].coords[0])
    for name,aa,bb in [
       ('BRIDGES_MAIN_WEST',ringpoint('MAIN',(-930,120)),ringpoint('WEST',(-1050,-480))),
       ('BRIDGES_MAIN_EAST',ringpoint('MAIN',(950,80)),ringpoint('EAST',(950,-500))),
       ('BRIDGES_WEST_LINK',ringpoint('WEST',(-440,-1180)),np.array([80,-1150])),
       ('BRIDGES_EAST_LINK',np.array([80,-1150]),ringpoint('EAST',(320,-1180)))]:
        q=LineString([aa,bb]);L=q.length;za=float(height([aa])[0]) if land.buffer(1).covers(Point(aa)) else 10.;zb=float(height([bb])[0]) if land.buffer(1).covers(Point(bb)) else 10.
        def bz(xy,q=q,L=L,za=za,zb=zb):
            t=np.array([q.project(Point(v))/L for v in np.asarray(xy).reshape(-1,2)]);return za+(zb-za)*smoothstep(t)+3*np.sin(np.pi*t)**2
        add(name,q,'BRIDGES',15,2.5,'WATER_BRIDGES',bz,True,False)
    # Node only crossings at a common elevation. Over/under crossings remain separate.
    endpoints=MultiPoint([p for r in routes for p in [r['line'].coords[0],r['line'].coords[-1]]])
    for r in routes:r['line']=shapely.snap(r['line'],endpoints,.02)
    split=[{0.,r['line'].length} for r in routes];separations=[];tree=shapely.STRtree([r['line'] for r in routes])
    for i,r in enumerate(routes):
        for j in tree.query(r['line'].buffer(.02)):
            j=int(j)
            if j<=i:continue
            other=routes[j];g=r['line'].intersection(other['line']);pp=parts(g,'Point')
            for seg in parts(g,'LineString'):pp.extend([Point(seg.coords[0]),Point(seg.coords[-1])])
            for v in pp:
                xy=np.array(v.coords[0]);z0=float(r['zfn']([xy])[0]);z1=float(other['zfn']([xy])[0]);dz=abs(z0-z1)
                if dz<.08:split[i].add(r['line'].project(v));split[j].add(other['line'].project(v))
                elif dz>=5.5:separations.append({'xy':xy.tolist(),'upper':r['name'] if z0>z1 else other['name'],'lower':other['name'] if z0>z1 else r['name'],'top_separation_m':dz})
                else:raise ValueError(('invalid layered crossing',r['name'],other['name'],xy,dz))
    nodes=[];lookup={};edges=[]
    def node(xy,z):
        key=(*np.round(xy,2),round(z,2))
        if key not in lookup:lookup[key]=len(nodes);nodes.append({'xy':np.asarray(xy).tolist(),'z':float(z),'edges':[],'radius':0.})
        return lookup[key]
    for r,ds in zip(routes,split):
        ds=sorted(ds)
        for start,stop in zip(ds[:-1],ds[1:]):
            if stop-start<.04:continue
            line=substring(r['line'],start,stop);xy=np.array([line.interpolate(v).coords[0] for v in np.linspace(0,line.length,max(3,int(line.length/3)+1))]);zs=r['zfn'](xy)
            ia=node(xy[0],zs[0]);ib=node(xy[-1],zs[-1]);e={k:v for k,v in r.items() if k not in ['line','zfn']};e.update(a=ia,b=ib,xy=xy,length=float(line.length),original_width=r['carriage_width']+3)
            ei=len(edges);edges.append(e);nodes[ia]['edges'].append(ei);nodes[ib]['edges'].append(ei)
    # Engineer nodal grades before fitting flat intersection mouths and smooth ramps.
    adjacency=[[] for _ in nodes]
    for e in edges:
        L=e['length'];ra=min(12.,L*.24);rb=ra;e['mouths']=[ra,rb]
        cost=.055*max(.01,L-ra-rb)
        if e['name']=='MAIN_EW_230' and all(189.9<=nodes[i]['xy'][0]<=350.1 for i in [e['a'],e['b']]):cost=0. # locally level frontage, retaining city-wide relief
        adjacency[e['a']].append((e['b'],cost));adjacency[e['b']].append((e['a'],cost))
    heights=np.array([n['z'] for n in nodes]);heap=[(float(h),i) for i,h in enumerate(heights)];heapq.heapify(heap)
    while heap:
        z,i=heapq.heappop(heap)
        if z>heights[i]+1e-9:continue
        for j,cost in adjacency[i]:
            if z+cost<heights[j]-1e-9:heights[j]=z+cost;heapq.heappush(heap,(z+cost,j))
    for n,h in zip(nodes,heights):n['z']=float(h)
    # Round endpoint coordinates to the shared node, so there are no numerical seam gaps.
    for e in edges:
        xy=e.pop('xy');xy[0]=nodes[e['a']]['xy'];xy[-1]=nodes[e['b']]['xy'];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))];L=s[-1]
        def mouth(ni):
            n=nodes[ni];v=xy[1]-xy[0] if ni==e['a'] else xy[-2]-xy[-1];v/=np.linalg.norm(v);values=[2.]
            for jj in n['edges']:
                other=edges[jj]
                if other is e:continue
                a0=np.array(nodes[other['a']]['xy']);b0=np.array(nodes[other['b']]['xy']);t=b0-a0;t/=max(np.linalg.norm(t),1e-8)
                if abs(float(v@t))<.97:values.append(other['width']/2+1.2)
            return min(max(values),L*.24)
        ra,rb=e.pop('mouths');za=nodes[e['a']]['z'];zb=nodes[e['b']]['z'];u=np.clip((s-ra)/max(L-ra-rb,.01),0,1);z=za+(zb-za)*smoothstep(u)
        e.update(points=np.c_[xy,z].tolist(),length=float(L),range=[ra,float(L-rb)],max_grade=float(np.max(np.abs(np.diff(z))/np.maximum(np.diff(s),1e-9))))
    seen=set();todo=[0]
    while todo:
        i=todo.pop()
        if i in seen:continue
        seen.add(i)
        for ei in nodes[i]['edges']:e=edges[ei];todo.append(e['b'] if e['a']==i else e['a'])
    if len(seen)!=len(nodes):raise ValueError(('disconnected graph',len(nodes)-len(seen),[nodes[i] for i in range(len(nodes)) if i not in seen][:8]))
    if max(e['max_grade'] for e in edges)>.087:raise ValueError(('steep roads',[(e['name'],e['max_grade'],e['length']) for e in edges if e['max_grade']>.087]))
    for crossing in separations:
        heights={}
        for name in ['upper','lower']:
            q=Point(crossing['xy']);e=min([e for e in edges if e['name']==crossing[name]],key=lambda e:LineString(np.array(e['points'])[:,:2]).distance(q));ln=LineString(np.array(e['points'])[:,:2]);heights[name]=float(frame(e,ln.project(q))[0][2])
        crossing['top_separation_m']=heights['upper']-heights['lower'];crossing['deck_underside_clearance_m']=crossing['top_separation_m']-1.1
        if crossing['deck_underside_clearance_m']<5.5:raise ValueError(('insufficient flyover clearance',crossing))
    ground=[e for e in edges if e['layer'].startswith('GROUND') or e['layer'].endswith('UPPER')];projector=SurfaceProjector([e for e in ground if not e['layer'].endswith('UPPER')]+[e for e in ground if e['layer'].endswith('UPPER') and min(np.array(e['points'])[:,2])<12])
    # The ground surface underneath both flyovers uses the lower roads' levels.
    ground=[e for e in edges if e['layer'].startswith('GROUND')];projector=SurfaceProjector(ground)
    footprints={}
    for layer in sorted({e['layer'] for e in edges}):
        ee=[e for e in edges if e['layer']==layer];pp=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,quad_segs=4) for e in ee]);ff=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,quad_segs=4) for e in ee]);footprints[layer]={'road':pp,'full':ff}
    allfull=unary_union([g['full'] for g in footprints.values()]);groundfull=unary_union([g['full'] for k,g in footprints.items() if k.startswith('GROUND')]);reserved=unary_union([unary_union([g['full'] for k,g in footprints.items() if k.startswith(prefix)]).convex_hull.buffer(12) for prefix in ['IX_A_RAMP','IX_B_RAMP']])
    real=json.loads(a.descriptors.read_text());row=[r for r in real if r['instance_name'] in ['OLDTOWN_Connected_Arcade_06','OLDTOWN_Connected_Arcade_07','OLDTOWN_Connected_Arcade_05','OLDTOWN_Connected_Shop_08','OLDTOWN_Connected_Shop_09','OLDTOWN_Corner_Shop_10']];cursor=342.45-sum(r['right']-r['left'] for r in row)+.035*5
    for r in row:r.update(anchor=[cursor,237.525],theta=0.);cursor+=r['right']-r['left']-.035
    for r in real:
        n=r['instance_name']
        if n=='OLDTOWN_Apartment_02':r.update(anchor=[-145,417.525],theta=0.)
        elif n=='OLDTOWN_Apartment_03':r.update(anchor=[-105,417.525],theta=0.)
        elif n=='OLDTOWN_Apartment_11':r.update(anchor=[-30,237.525],theta=0.)
        elif n=='CBD_Modern_Glass_02':r.update(anchor=[-381.975,1190],theta=-math.pi/2,setback_m=18.)
        elif n=='CBD_Office_Building_01':r.update(anchor=[-381.975,1115],theta=-math.pi/2,setback_m=18.)
        theta=r['theta'];R=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]]);lo,hi=np.array(r['rotated_xy_bounds']);rect=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]);xy=(rect-[r['left'],r['front']])@R.T+np.array(r['anchor']);poly=Polygon(xy);frontsamples=np.array(r['anchor'])+np.linspace(0,r['right']-r['left'],41)[:,None]*R[:,0]-R[:,1]*.04;base=float(np.mean(projector.height(frontsamples))+.16)
        r.update(center=poly.centroid.coords[0],region='MAIN',footprint_xy=xy.tolist(),pad_xy=shapely.get_coordinates(poly.buffer(.13,join_style=2)).tolist(),floor=base,foundation_bottom_m=float(min(terrain_height(xy,islands,lake,projector).min(),base)-.4),source_filename=r['file'],angle=theta+r['turn'],direct_sidewalk_frontage=True)
        if r.get('setback_m'):
            u=R[:,0];v=R[:,1];anchor=np.array(r['anchor']);width=r['right']-r['left'];end=anchor+u*width/2-v*(r['setback_m']+.05);r['floor']=float(projector.height([end])[0]+.16);r['access_start_xy']=(anchor+u*width/2).tolist();r['access_end_xy']=end.tolist();r['plaza_xy']=np.array([anchor,anchor+u*width,anchor+u*width-v*(r['setback_m']+.05),anchor-v*(r['setback_m']+.05)]).tolist();r['direct_sidewalk_frontage']=False
    sourcepads=unary_union([Polygon(r['pad_xy']) for r in real]+[Polygon(r['plaza_xy']) for r in real if 'plaza_xy' in r]);openparcels=land.buffer(-35).difference(allfull).difference(reserved);parcels=[q for q in parts(openparcels,'Polygon') if 300<q.area<155000]
    # Select connected, graded pedestrian links first; lots subsequently respect them.
    alleys=[]
    for frac in [.5,.23,.77,.37,.63]:
        for parcel in sorted(parcels,key=lambda q:(q.centroid.y,q.centroid.x)):
            c=parcel.centroid;x0,y0,x1,y1=parcel.bounds
            if not islands['MAIN'].covers(c) or c.y<50 or c.y>800 or c.x<-850 or c.x>1250:continue
            if frac!=.5 and x1-x0<100:continue
            xx=x0+(x1-x0)*frac;g=LineString([(xx,y0-20),(xx,y1+20)]).intersection(parcel)
            for ln in parts(g,'LineString'):
                if not 28<ln.length<340:continue
                ep=np.array([ln.coords[0],ln.coords[-1]]);ep[0,1]-=.06;ep[-1,1]+=.06;ln=LineString(ep)
                if not all(groundfull.buffer(.002).covers(Point(v)) for v in ep):continue
                if ln.buffer(2.3).intersects(sourcepads.buffer(.8)):continue
                if any(ln.distance(LineString(q['points']))<8 for q in alleys):continue
                z=projector.height(ep)+.143577;grade=float(abs(z[1]-z[0])/ln.length)
                if grade>.06:continue
                alleys.append({'name':f'MAIN_OLD_ALLEY_{len(alleys)+1:03d}','points':ep.tolist(),'end_heights':z.tolist(),'width':3.6,'length':ln.length,'max_grade':grade})
                if len(alleys)>=119:break
            if len(alleys)>=119:break
        if len(alleys)>=119:break
    alleymask=unary_union([LineString(q['points']).buffer(q['width']/2+.4,cap_style=2) for q in alleys]);exclude=unary_union([allfull.buffer(.025),sourcepads.buffer(.35),alleymask,reserved]);lots=[];rng=np.random.default_rng(13058)
    def zone(x,y,reg):
        if reg=='EAST':return 'INDUSTRIAL'
        if reg=='WEST':return 'PARK' if x<-1300 and y>-1000 else 'VILLAGE'
        if 60<y<620 and -680<x<740:return 'OLDTOWN'
        if -600<x<600 and y>700:return 'CBD'
        if x>600 and y>650:return 'CIVIC'
        if x<-680 and y>450:return 'UNIVERSITY'
        if y>1340:return 'PARK'
        return 'RESIDENTIAL'
    def addlot(poly,reg,z,h):
        if poly.area<20 or not land.covers(poly) or poly.intersects(exclude):return
        coords=shapely.get_coordinates(poly)[:-1];base=float(max(terrain_height(coords,islands,lake,projector)));center=poly.centroid.coords[0]
        lots.append({'name':f'{reg}_{z}_{len(lots):05d}','region':reg,'zone':z,'center':list(center),'footprint':coords.tolist(),'base':base,'height':float(h),'size':[poly.bounds[2]-poly.bounds[0],poly.bounds[3]-poly.bounds[1],float(h)]})
    # Block perimeter rows sit on sidewalk edges; interiors form courts and rear lanes.
    for parcel in parcels:
        c=parcel.centroid;reg=next((k for k,v in islands.items() if v.covers(c)),None)
        if reg is None:continue
        z=zone(c.x,c.y,reg);x0,y0,x1,y1=parcel.bounds
        if z=='PARK':continue
        if z=='OLDTOWN':
            depth=17.;inner=parcel.buffer(-.025);cols=max(1,round((x1-x0)/10.5));ww=(x1-x0)/cols
            for side in [-1,1]:
                yy=y0+.03 if side<0 else y1-depth-.03
                for xx in np.linspace(x0+.03,x1-ww-.03,cols):
                    p=box(xx,yy,xx+ww-.10,yy+depth)
                    if inner.covers(p):addlot(p,reg,z,rng.choice([7.2,9.6,12.0,14.4]))
            for xx in [x0+.03,x1-depth-.03]:
                for yy in np.arange(y0+depth+.5,y1-depth-7,10.5):
                    p=box(xx,yy,xx+depth,yy+10.3)
                    if inner.covers(p):addlot(p,reg,z,rng.choice([7.2,9.6,12.0]))
            for xx in np.arange(x0+depth+3,x1-depth-8,10.5):
                for yy in np.arange(y0+depth+6,y1-depth-13,23):
                    p=box(xx,yy,xx+10.3,yy+16)
                    if parcel.covers(p):addlot(p,reg,z,rng.choice([7.2,9.6,12.]))
        else:
            pitch={'CBD':(64,68),'RESIDENTIAL':(45,53),'CIVIC':(66,75),'UNIVERSITY':(60,70),'VILLAGE':(35,42),'INDUSTRIAL':(96,80)}[z]
            dims={'CBD':(43,48),'RESIDENTIAL':(26,32),'CIVIC':(42,50),'UNIVERSITY':(36,45),'VILLAGE':(22,28),'INDUSTRIAL':(70,48)}[z]
            for xx in np.arange(x0+4,x1-dims[0],pitch[0]):
                for yy in np.arange(y0+4,y1-dims[1],pitch[1]):
                    p=box(xx,yy,xx+dims[0],yy+dims[1])
                    if not parcel.covers(p):continue
                    h={'CBD':(48,126),'RESIDENTIAL':(18,34),'CIVIC':(15,27),'UNIVERSITY':(14,24),'VILLAGE':(7,13),'INDUSTRIAL':(9,18)}[z];addlot(p,reg,z,rng.uniform(*h))
    bridgearea=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in edges if e['bridge']]);totalplay=land.union(bridgearea).area
    coverage=sum(Polygon(b['footprint']).area for b in lots)+sum(Polygon(b['footprint_xy']).area for b in real);oldwindow=box(-680,60,740,620).intersection(land);oldcover=sum(Polygon(b['footprint']).intersection(oldwindow).area for b in lots)+sum(Polygon(b['footprint_xy']).intersection(oldwindow).area for b in real)
    p={'schema':'hero13.city.reconstruction.v8','units':'metres','coasts':{k:shapely.get_coordinates(v.exterior).tolist() for k,v in islands.items()},'lake':shapely.get_coordinates(lake.exterior).tolist(),'nodes':nodes,'edges':edges,'buildings':lots,'real_buildings':real,'pedestrian_alleys':alleys,'grade_separated_crossings':separations,'interchanges':[{'name':'CENTRAL_DIAMOND','center':[80,950],'upper':'MAIN_EW_950','lower':'MAIN_NS_80','ramps':4},{'name':'EAST_CITY_FLYOVER','center':[860,650],'upper':'MAIN_NS_860','lower':'MAIN_EW_650','ramps':2}],'connected_arcades':{'front_origin':[280,237.525],'instances':[r['instance_name'] for r in row],'corner_position':'right','corner_turn_degrees':90,'added_canopy_present':False,'frontage_flush_to_sidewalk':True},'sources':json.loads(a.baseline.read_text())['sources'],'stats':{'land_area_m2':land.area,'land_plus_bridge_play_area_m2':totalplay,'water_excluded':True,'road_length_m':sum(e['length'] for e in edges),'road_edges':len(edges),'junctions':len(nodes),'graph_components':1,'max_grade':max(e['max_grade'] for e in edges),'buildings':len(lots)+len(real),'placeholder_lots':len(lots),'real_buildings':len(real),'pedestrian_alleys':len(alleys),'interchanges':2,'ramps':6,'building_coverage_percent':100*coverage/land.area,'oldtown_coverage_percent':100*oldcover/oldwindow.area,'global_scale_applied':False}}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'compact_plan_summary.json').write_text(json.dumps(p['stats'],indent=2));(a.out/'playable_boundary.geojson').write_text(shapely.to_geojson(land));print(json.dumps(p['stats'],indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--descriptors',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);main(ap.parse_args())
