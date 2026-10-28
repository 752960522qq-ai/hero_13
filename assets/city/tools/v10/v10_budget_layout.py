"""Fresh street blocks and an explicit <=699 independent-building budget."""
import json,collections,math
from pathlib import Path
from compact_city_math import *
from shapely.geometry import box

TARGETS={'OLDTOWN':280,'RESIDENTIAL':110,'CBD':60,'CIVIC':10,'UNIVERSITY':20,'VILLAGE':100,'INDUSTRIAL':60}
def parts(g,kind):return [q for q in shapely.get_parts(g) if q.geom_type==kind and not q.is_empty]

def finish_layout(a,islands,lake,land,routes,nodes,edges,separations,projector,footprints,allfull,groundfull,reserved,real,row,parcels):
    # Rebuild the rear passage and re-seat both original back-lane houses.
    lane={'name':'MAIN_BACKLANE_SOURCE_HOUSES','points':[[194.94,260.],[343.56,260.]],'width':3.6}
    ep=np.array(lane['points']);L=float(np.linalg.norm(ep[1]-ep[0]));hh=projector.height(ep)+.143577;lane.update(length=L,end_heights=hh.tolist(),max_grade=float(abs(hh[1]-hh[0])/L));alleys=[lane]
    for original in json.loads(a.descriptors.read_text()):
        if not original['instance_name'].startswith('OLDTOWN_Backlane_'):continue
        r=dict(original);w=r['right']-r['left'];r['floor']=float(np.interp(r['anchor'][0]+w/2,ep[:,0],hh)+.006);r['foundation_bottom_m']=float(min(terrain_height(np.array(r['pad_xy']),islands,lake,projector).min(),r['floor'])-.45);r['direct_sidewalk_frontage']=False;r['direct_alley_frontage']=True;r['access_alley']=lane['name'];real.append(r)
    for r in real:r['building_count_units']=1
    sourcepads=unary_union([Polygon(r['pad_xy']) for r in real]+[Polygon(r['plaza_xy']) for r in real if 'plaza_xy' in r])
    # Fewer, purposeful cross-block lanes; every endpoint touches an existing sidewalk.
    for parcel in sorted(parcels,key=lambda q:(q.centroid.y,q.centroid.x)):
        c=parcel.centroid;x0,y0,x1,y1=parcel.bounds
        if not islands['MAIN'].covers(c) or not (-450<c.x<700 and 70<c.y<620):continue
        for frac in ([.5] if x1-x0<230 else [.35,.68]):
            xx=x0+(x1-x0)*frac
            for ln in parts(LineString([(xx,y0-20),(xx,y1+20)]).intersection(parcel),'LineString'):
                if not 35<ln.length<310:continue
                ends=np.array([ln.coords[0],ln.coords[-1]]);ends[0,1]-=.06;ends[-1,1]+=.06;ln=LineString(ends)
                if not all(groundfull.buffer(.002).covers(Point(v)) for v in ends):continue
                if ln.buffer(2.35).intersects(sourcepads.buffer(.8)):continue
                if any(ln.distance(LineString(q['points']))<8 for q in alleys):continue
                z=projector.height(ends)+.143577;grade=float(abs(z[1]-z[0])/ln.length)
                if grade>.06:continue
                alleys.append({'name':f'MAIN_REBUILT_LANE_{len(alleys):03d}','points':ends.tolist(),'end_heights':z.tolist(),'width':3.6,'length':ln.length,'max_grade':grade})
    alleymask=unary_union([LineString(q['points']).buffer(q['width']/2+.4,cap_style=2) for q in alleys]);exclude=unary_union([allfull.buffer(.025),sourcepads.buffer(.35),alleymask,reserved]);rng=np.random.default_rng(130610);groups=collections.defaultdict(list);candidates=collections.Counter();block_shapes=collections.defaultdict(list)
    def zone(x,y,reg):
        if reg=='WEST':return 'VILLAGE'
        if reg=='EAST':return 'INDUSTRIAL'
        if 60<y<500 and -420<x<490:return 'OLDTOWN'
        if -480<x<480 and y>600:return 'CBD'
        if x>480 and y>560:return 'CIVIC'
        if x<-480 and y>520:return 'UNIVERSITY'
        return 'RESIDENTIAL'
    def candidate(poly,reg,z,h,block,side,kind):
        if poly.area<50 or not land.covers(poly) or poly.intersects(exclude):return
        if any(poly.intersection(other).area>.001 for other in block_shapes[block]):return
        block_shapes[block].append(poly)
        coords=np.asarray(poly.exterior.coords)[:-1];center=poly.centroid.coords[0];base=float(max(terrain_height(coords,islands,lake,projector)));name=f'{reg}_{z}_{candidates[z]:04d}'
        r={'name':name,'region':reg,'zone':z,'center':list(center),'footprint':coords.tolist(),'base':base,'height':float(h),'size':[poly.bounds[2]-poly.bounds[0],poly.bounds[3]-poly.bounds[1],float(h)],'block_id':block,'frontage_group':f'{block}:{side}','typology':kind,'building_count_units':1,'count_basis':'one independent footprint; connected building massing'}
        groups[z].append(r);candidates[z]+=1
    for bi,parcel in enumerate(parcels):
        c=parcel.centroid;reg=next((k for k,v in islands.items() if v.covers(c)),None)
        if reg is None:continue
        z=zone(c.x,c.y,reg);x0,y0,x1,y1=parcel.bounds
        if z=='OLDTOWN':
            depth=23.;inner=parcel.buffer(-.025);cols=max(1,int((x1-x0)/29.));ww=(x1-x0)/cols
            for side in [-1,1]:
                yy=y0+.03 if side<0 else y1-depth-.03
                for xx in np.linspace(x0+.03,x1-ww-.03,cols):
                    q=box(xx,yy,xx+ww-.18,yy+depth)
                    if inner.covers(q):candidate(q,reg,z,rng.choice([9.6,12.,14.4]),bi,f'H{side}','street_house')
            for side,xx in enumerate([x0+.03,x1-depth-.03]):
                for yy in np.arange(y0+depth+.5,y1-depth-16,29.):
                    q=box(xx,yy,xx+depth,yy+28.5)
                    if inner.covers(q):candidate(q,reg,z,rng.choice([9.6,12.,14.4]),bi,f'V{side}','street_house')
            for xx in np.arange(x0+depth+4,x1-depth-19,34.):
                for yy in np.arange(y0+depth+7,y1-depth-23,37.):
                    q=box(xx,yy,xx+22,yy+24)
                    if parcel.covers(q):candidate(q,reg,z,rng.choice([7.2,9.6,12.]),bi,'INNER','backlane_house')
        else:
            pitch={'CBD':(50,56),'RESIDENTIAL':(40,45),'CIVIC':(47,55),'UNIVERSITY':(45,54),'VILLAGE':(39,43),'INDUSTRIAL':(75,57)}[z]
            dims={'CBD':(36,42),'RESIDENTIAL':(26,34),'CIVIC':(34,42),'UNIVERSITY':(32,42),'VILLAGE':(25,30),'INDUSTRIAL':(62,42)}[z]
            for xx in np.arange(x0+3,x1-dims[0],pitch[0]):
                for yy in np.arange(y0+3,y1-dims[1],pitch[1]):
                    q=box(xx,yy,xx+dims[0],yy+dims[1])
                    if not parcel.covers(q):continue
                    hh={'CBD':(38,95),'RESIDENTIAL':(15,30),'CIVIC':(12,24),'UNIVERSITY':(12,23),'VILLAGE':(7.2,13),'INDUSTRIAL':(9,17)}[z];candidate(q,reg,z,rng.uniform(*hh),bi,'INTERIOR',z.lower())
    realcounts=collections.Counter('CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN' for r in real);lots=[]
    focus={'OLDTOWN':(180,280),'CBD':(-90,900),'RESIDENTIAL':(-300,400),'CIVIC':(730,870),'UNIVERSITY':(-640,800),'VILLAGE':(-920,-770),'INDUSTRIAL':(740,-810)}
    for z,total in TARGETS.items():
        want=total-realcounts[z];pool=groups[z]
        if len(pool)<want:raise ValueError(('insufficient independent sites',z,len(pool),want,dict(candidates)))
        if z=='OLDTOWN':
            # Fill complete frontage groups near the historic core before short leftovers.
            bygroup=collections.defaultdict(list)
            for r in pool:bygroup[r['frontage_group']].append(r)
            def key(items):
                co=np.mean([r['center'] for r in items],axis=0);return (0 if items[0]['typology']=='street_house' else 1,float(np.linalg.norm(co-np.array(focus[z]))))
            order=[]
            for group in sorted(bygroup.values(),key=key):order.extend(sorted(group,key=lambda r:r['center']))
            chosen=order[:want]
        else:
            # Spatially spread sites across parcels; keep additional floor area as landscape/courts.
            byblock=collections.defaultdict(list)
            for r in pool:byblock[r['block_id']].append(r)
            blocks=sorted(byblock,key=lambda b:np.linalg.norm(np.mean([r['center'] for r in byblock[b]],axis=0)-focus[z]));chosen=[]
            for block in blocks:byblock[block].sort(key=lambda r:np.linalg.norm(np.array(r['center'])-focus[z]))
            while len(chosen)<want:
                for block in blocks:
                    if byblock[block] and len(chosen)<want:chosen.append(byblock[block].pop(0))
        lots.extend(chosen)
    assert len(lots)+len(real)==640 and sum(TARGETS.values())==640
    # Validate that the new budget is represented by distinct, nonoverlapping footprints.
    polys=[Polygon(b['footprint']) for b in lots]+[Polygon(r['footprint_xy']) for r in real];tree=shapely.STRtree(polys)
    for i,poly in enumerate(polys):
        for j in tree.query(poly):
            if j<=i or (i>=len(lots) and j>=len(lots)):continue
            assert poly.intersection(polys[j]).area<.001,('overlapping buildings',i,int(j))
    bridgearea=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in edges if e['bridge']]);oldwindow=box(-420,60,490,500).intersection(land);coverage=unary_union(polys)
    stats={'land_area_m2':land.area,'land_plus_bridge_play_area_m2':land.union(bridgearea).area,'water_excluded':True,'road_length_m':sum(e['length'] for e in edges),'road_edges':len(edges),'junctions':len(nodes),'graph_components':1,'max_grade':max(e['max_grade'] for e in edges),'buildings':len(lots)+len(real),'placeholder_lots':len(lots),'real_buildings':len(real),'building_limit':699,'building_count_by_zone':TARGETS,'pedestrian_alleys':len(alleys),'interchanges':2,'ramps':6,'building_coverage_percent':100*coverage.area/land.area,'oldtown_coverage_percent':100*coverage.intersection(oldwindow).area/oldwindow.area,'global_scale_applied':False}
    p={'schema':'hero13.city.reconstruction.v10','units':'metres','coasts':{k:shapely.get_coordinates(v.exterior).tolist() for k,v in islands.items()},'lake':shapely.get_coordinates(lake.exterior).tolist(),'nodes':nodes,'edges':edges,'buildings':lots,'real_buildings':real,'pedestrian_alleys':alleys,'grade_separated_crossings':separations,'interchanges':[{'name':'CENTRAL_DIAMOND','center':[80,950],'upper':'MAIN_EW_950','lower':'MAIN_NS_80','ramps':4},{'name':'EAST_CITY_FLYOVER','center':[620,650],'upper':'MAIN_NS_620','lower':'MAIN_EW_650','ramps':2}],'connected_arcades':{'front_origin':[280,237.525],'instances':[r['instance_name'] for r in row],'corner_position':'right','corner_turn_degrees':90,'added_canopy_present':False,'frontage_flush_to_sidewalk':True},'sources':json.loads(a.baseline.read_text())['sources'],'stats':stats,'district_cuts':{'MAIN':{'x':[-500,0,500],'y':620},'WEST':{'x':-950,'y':-720},'EAST':{'x':750,'y':-800}},'building_count_policy':'Each placeholder is a separate nonoverlapping footprint and connected volume. Each retained original source building is counted once. Mesh batching never reduces the count.'}
    assert 3e6<=land.area<=3.5e6 and 3e6<=stats['land_plus_bridge_play_area_m2']<=3.5e6
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'compact_plan_summary.json').write_text(json.dumps({'stats':stats,'candidate_counts':dict(candidates)},indent=2));print('V10_PLAN_COMPLETE',json.dumps(stats),flush=True)
