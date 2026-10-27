"""Plan a denser CBD and two residential placements without obstructing roads.

Coordinates are Blender metres. The final terrain and exact mesh checks happen
in urban_update_blender.py against the editable city scene.
"""
import argparse, json, math, random
from pathlib import Path
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union, nearest_points

ap=argparse.ArgumentParser()
ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args()
p=json.loads(args.plan.read_text())
rng=random.Random(13261027)
edges=[]
for e in p['edges']:
    line=LineString([(q[0],q[1]) for q in e['points']])
    if line.length:
        edges.append((e,line))
road_buffer=unary_union([line.buffer(e['width']/2+2.5,cap_style='round',join_style='round') for e,line in edges])
carriage=unary_union([line.buffer(max(.1,e['width']/2-2.85),cap_style='round',join_style='round') for e,line in edges])
old=[b for b in p['buildings'] if b['zone']=='OLDTOWN']
all_boxes={b['name']:Polygon(b['footprint']) for b in p['buildings']}
real_pads=[Polygon(b['footprint_xy']) for b in p['real_buildings']]
real_paths=[LineString([b['access_start_xy'],b['access_end_xy']]).buffer(b['access_width_m']/2+.5) for b in p['real_buildings']]
static=unary_union(list(all_boxes.values())+real_pads+real_paths)

def building_rect(center,w,d,angle):
    c,s=math.cos(angle),math.sin(angle)
    a=np.array([c,s]);b=np.array([-s,c]);q=np.array(center)
    return Polygon([q-a*w/2-b*d/2,q+a*w/2-b*d/2,q+a*w/2+b*d/2,q-a*w/2+b*d/2])

def site_candidates(model, target_height):
    # Source dimensions as measured from the glTF accessor, including aprons.
    dims={'apartment_2':[.78982556,.52697760,.97894287],
          'apartment_3':[.79656994,.42897040,.97924805]}[model]
    w,d=[v*target_height/dims[2] for v in dims[:2]]
    output=[]
    for b in old:
        center=np.array(b['center'],float)
        nearby=sorted([(line.distance(Point(center)),e,line) for e,line in edges if e['region']=='MAIN'],key=lambda r:r[0])
        for distance,e,line in nearby[:4]:
            if not (24<distance<55):continue
            q=np.array(nearest_points(Point(center),line)[1].coords[0]);front=(q-center)/np.linalg.norm(q-center)
            angle=math.atan2(front[0],-front[1])
            pad=building_rect(center,w+2,d+2,angle)
            if pad.intersects(road_buffer):continue
            obstacles=unary_union([geom for name,geom in all_boxes.items() if name!=b['name']]+real_pads+real_paths)
            if pad.buffer(3).intersects(obstacles):continue
            start=center+front*((d+2)/2-.15)
            end=q-front*(e['width']/2-1.4)
            if np.linalg.norm(end-start)<3:continue
            access=LineString([start,end]).buffer(1.5,cap_style='flat')
            if access.buffer(.25).intersects(obstacles) or access.intersects(carriage):continue
            # Access should leave enough clear open space at the side of the pad.
            output.append({'model':model,'target_height_m':target_height,'placeholder':b['name'],'center':center.tolist(),
              'angle':angle,'road_name':e['name'],'road_nearest':q.tolist(),'road_halfwidth':e['width']/2,
              'pad_xy':[list(q) for q in list(pad.exterior.coords)[:-1]],'access_start_xy':start.tolist(),
              'access_end_xy':end.tolist(),'approx_access_length_m':float(np.linalg.norm(end-start)),
              'approx_source_size_m':[w,d,target_height]})
            break
    return output

one=site_candidates('apartment_2',23.0);two=site_candidates('apartment_3',23.5)
pairs=[]
for a in one:
    for b in two:
        if a['placeholder']==b['placeholder']:continue
        dist=math.dist(a['center'],b['center'])
        if not 32<dist<95:continue
        if Polygon(a['pad_xy']).buffer(3).intersects(Polygon(b['pad_xy'])):continue
        if LineString([a['access_start_xy'],a['access_end_xy']]).buffer(1.5).intersects(Polygon(b['pad_xy'])):continue
        if LineString([b['access_start_xy'],b['access_end_xy']]).buffer(1.5).intersects(Polygon(a['pad_xy'])):continue
        center=(np.array(a['center'])+np.array(b['center']))/2
        # Place both in the inner old-town core and preferably on one street.
        score=(0 if a['road_name']==b['road_name'] else 45)+abs(dist-55)*.2+abs(center[0]+250)*.012+abs(center[1]-300)*.02+.15*(a['approx_access_length_m']+b['approx_access_length_m'])
        pairs.append((score,a,b))
pairs.sort(key=lambda item:item[0])
if not pairs:raise RuntimeError('No safe pair of old-town lots')
print('OLDTOWN_CANDIDATES',len(one),len(two),'pairs',len(pairs))
for score,a,b in pairs[:8]:
    print('PAIR',round(score,2),a['placeholder'],[round(x,1) for x in a['center']],a['road_name'],b['placeholder'],[round(x,1) for x in b['center']],b['road_name'])

# Main-island CBD follows the zone defined in create_city_plan.py (reference px).
cbd=box((345-440)*4.6,(450-316)*4.6,(603-440)*4.6,(450-168)*4.6)
# Reserve a few small green pockets on currently open ground.
parks=[]
for _ in range(2500):
    x=rng.uniform(cbd.bounds[0]+30,cbd.bounds[2]-30);y=rng.uniform(cbd.bounds[1]+30,cbd.bounds[3]-30)
    radius=rng.uniform(18,26);circle=Point(x,y).buffer(radius,quad_segs=12)
    if circle.buffer(5).intersects(static) or circle.intersects(road_buffer):continue
    if any(circle.buffer(75).intersects(q) for q in parks):continue
    parks.append(circle)
    if len(parks)==5:break
avoid=unary_union([road_buffer,static]+parks)
candidates=[]
for _ in range(10000):
    x=rng.uniform(cbd.bounds[0]+18,cbd.bounds[2]-18);y=rng.uniform(cbd.bounds[1]+18,cbd.bounds[3]-18)
    w=rng.uniform(20,32);d=rng.uniform(20,32)
    footprint=box(x-w/2,y-d/2,x+w/2,y+d/2)
    if not cbd.contains(footprint) or footprint.buffer(3).intersects(avoid):continue
    # Lower podium massing interspersed with taller towers for a varied skyline.
    h=rng.uniform(42,72) if rng.random()<.24 else rng.uniform(72,138)
    record={'name':'MAIN_CBD_Infill_%03d'%len(candidates),'region':'MAIN','zone':'CBD',
            'center':[x,y],'size':[w,d,h],'footprint':[list(q) for q in footprint.exterior.coords]}
    candidates.append(record)
    avoid=unary_union([avoid,footprint.buffer(4)])
    if len(candidates)==110:break
print('CBD_INFILL_CANDIDATES',len(candidates),'PARKS',len(parks))
manifest={'oldtown_candidate_pairs':[{'score':s,'instances':[a,b]} for s,a,b in pairs[:50]],
          'cbd_boundary':list(cbd.exterior.coords),'green_pockets':[list(p.exterior.coords) for p in parks],
          'cbd_infill_candidates':candidates}
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(manifest,indent=2))
