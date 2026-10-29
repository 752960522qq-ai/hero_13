"""Choose compact sites against the actual v14 street and building footprints."""
import sys,json,math,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
import numpy as np,shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.affinity import translate,rotate
p=json.load(open('/workspace/scratch/705f52588668/work_v14/model/city_plan.json'))
real=[r for r in p['real_buildings'] if r['instance_name'].startswith('CBD_') or r['instance_name'] in ['APT_V14_A32','APT_V14_A35']]
civic=[b for b in p['buildings'] if b['zone'] in ['CIVIC','GOVERNMENT']]
gov=next(r for r in p['real_buildings'] if r.get('zone')=='GOVERNMENT')
moving={r['instance_name'] for r in real+[gov]}|{b['name'] for b in civic}
land=unary_union([Polygon(q) for q in p['coasts'].values()]).difference(Polygon(p['lake']))
roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.8,join_style=2) for e in p['edges']])
carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.15,join_style=2) for e in p['edges']])
reservation=Polygon(p['cbd_plan']['tianming']['polygon'])
fixed=[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r['instance_name'] not in moving]+[Polygon(b['footprint']) for b in p['buildings'] if b['name'] not in moving]
occupied=unary_union(fixed+[reservation.buffer(.5)])
goals=[]
for e in p['edges']:
    if e['region']!='MAIN':continue
    if e['name'] in ['MAIN_EW_950','MAIN_NS_620']:continue # elevated deck has no street-level entrance
    line=LineString(np.array(e['points'])[:,:2])
    for side in ['left','right']:
        off=line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.65,side,join_style=2)
        for part in shapely.get_parts(off):
            if part.geom_type=='LineString':goals.append((e['name']+'_'+side,part))
cbd_area=box(-185,748,330,1085);gov_area=box(360,738,598,920)
sites=[]
def choices(r,area,kind):
    global occupied
    name=r.get('instance_name',r.get('name'));orig=Polygon(r.get('footprint_xy',r.get('footprint')));center=np.array(orig.centroid.coords[0]);basepoly=translate(orig,-center[0],-center[1]);cands=[]
    xs=np.arange(area.bounds[0]+12,area.bounds[2]-12,10.);ys=np.arange(area.bounds[1]+12,area.bounds[3]-12,10.)
    free=area.difference(unary_union([roads.buffer(2.),occupied.buffer(2.5)]));shapely.prepare(free)
    for turn in [0,90]:
        rel=rotate(basepoly,turn,origin=(0,0));grid=shapely.points(np.array(np.meshgrid(xs,ys)).reshape(2,-1).T)
        # Coarse rejection with vectorized centroid-to-obstacle distance.
        for cp in grid:
            x,y=cp.x,cp.y;poly=translate(rel,x,y)
            if not free.covers(poly):continue
            dd=Point(x,y).distance(Point(80,950))
            # Preference for the interchange's inner islands, then compact perimeter.
            inner=(-5<x<70 or 90<x<165) and 780<y<1120
            side=abs(x-80)<140 and abs(y-950)<150
            score=dd*.09-(8 if inner else 0)-(2 if side else 0)
            if kind=='gov':score=math.hypot(x-495,y-825)*.12
            cands.append((score,x,y,turn,poly))
    tested=[]
    localgoals=[g for g in goals if g[1].intersects(area.buffer(120.))]
    for score,x,y,turn,poly in sorted(cands,key=lambda v:v[0])[:100]:
            # Require a straight entrance route in the same block. Four facade directions
            # let the buildings face their nearest usable street without mirrors.
            faceoptions=[]
            for j in range(4):
                coords=np.array(poly.exterior.coords)[:4];aa,bb=coords[j],coords[(j+1)%4];mid=(aa+bb)/2;u=(bb-aa)/np.linalg.norm(bb-aa);normal=np.array([u[1],-u[0]])
                if poly.covers(Point(mid+normal*.5)):normal=-normal
                start=mid+normal*.08
                for gn,gl in sorted(localgoals,key=lambda g:g[1].distance(Point(start)))[:4]:
                    end=np.array(gl.interpolate(gl.project(Point(start))).coords[0]);route=LineString([start,end])
                    if route.length<2.5 or route.length>110:continue
                    corridor=route.buffer(1.7,cap_style=2)
                    if corridor.intersection(carriage).area>.001 or corridor.intersection(poly.buffer(-.03)).area>.001 or corridor.intersection(occupied).area>.001:continue
                    if not land.covers(corridor):continue
                    faceoptions.append((route.length,gn,start.tolist(),end.tolist(),[aa.tolist(),bb.tolist()]))
            if not faceoptions:continue
            L,gn,st,en,face=min(faceoptions)
            tested.append((score+L*.04,x,y,turn,poly,gn,st,en,face))
            if len(tested)>=8:break
    if not tested:raise RuntimeError(('no site',name,kind,len(sites),len(cands)))
    _,x,y,t,poly,gn,st,en,face=min(tested,key=lambda v:v[0]);occupied=unary_union([occupied,poly.buffer(4.)])
    site={'name':name,'kind':kind,'old_center':r['center'],'center':[x,y],'rotation_delta_degrees':t,'footprint':list(poly.exterior.coords)[:-1],'goal_name':gn,'route':[st,en],'front_edge':face}
    sites.append(site);print('SITE',name,site['center'],t,gn,flush=True)
# Larger sources first. Preserve all source scales and building identities.
for r in sorted(real,key=lambda r:Polygon(r['footprint_xy']).area,reverse=True):choices(r,cbd_area,'cbd')
choices(gov,gov_area,'gov')
for r in civic:choices(r,gov_area,'gov')
out={'sites':sites,'cbd_core_polygon':list(cbd_area.exterior.coords),'municipal_polygon':list(gov_area.exterior.coords),'office_reclassified':['APT_V14_A32','APT_V14_A35']}
(ROOT/'layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
