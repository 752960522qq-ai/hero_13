"""Create a geometry-aware redevelopment plan from the existing city.

This does not touch Blender files. Dimensions are game blockout targets, in
metres; all existing real building assets and their approach paths are protected.
"""
from pathlib import Path
import argparse, collections, copy, json, math, random
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union

ap=argparse.ArgumentParser()
ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
p=json.loads(args.plan.read_text());rng=random.Random(1327026)
old_edges=copy.deepcopy(p['edges']);old_nodes=copy.deepcopy(p['nodes'])
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def roadshape(edges):
    parts=[LineString(np.asarray(e['points'])[:,:2]).buffer(e['carriage_width']/2,cap_style='round',join_style='round',quad_segs=5) for e in edges]
    pavement=unary_union(parts).buffer(2.2,join_style='round',quad_segs=4).buffer(-2.2,join_style='round',quad_segs=4)
    pavement=shapely.set_precision(pavement,.001)
    full=pavement.buffer(3,join_style='round',quad_segs=5)
    return pavement,full
oldroad,oldfull=roadshape(old_edges)
merges=[
 ('M_Oldtown_Block_518',250,243),
 ('M_Oldtown_Block_595',251,77),
 ('M_CBD_Cross_355',213,70),
 ('M_Oldtown_Block_444',249,242),
]
repairs=[];patches=[]
for name,src,dst in merges:
    source=p['nodes'][src];target=p['nodes'][dst];assert len(source['edges'])==1
    eid=source['edges'][0];e=p['edges'][eid];assert e['name']==name
    q=np.asarray(e['points'],float);at_start=e['a']==src
    if not at_start:q=q[::-1].copy()
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
    delta=np.asarray(target['xy'])-np.asarray(source['xy']);dz=target['z']-source['z']
    blend=75.;w=1-smooth(d/blend)
    q[:,:2]+=w[:,None]*delta;q[:,2]+=w*dz
    q[0,:2]=target['xy'];q[0,2]=target['z']
    if not at_start:q=q[::-1]
    e['points']=q.tolist()
    if at_start:e['a']=dst
    else:e['b']=dst
    ds=np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1)
    e['length']=float(ds.sum());e['max_grade']=float(np.max(np.abs(np.diff(q[:,2]))/ds))
    ra=min(p['nodes'][e['a']]['radius'],e['length']*.42);rb=min(p['nodes'][e['b']]['radius'],e['length']*.42)
    e['range']=[ra,e['length']-rb]
    # Include the entire 75 m taper and nearby original intersection.
    changed=np.asarray(old_edges[eid]['points']);old_d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(changed[:,:2],axis=0),axis=1))]
    mask=old_d<=80 if at_start else old_d>=old_d[-1]-80
    bounds=np.vstack([changed[mask,:2],q[:,:2][mask],np.asarray(target['xy'])[None,:]])
    lo=bounds.min(0)-30;hi=bounds.max(0)+30
    patches.append(box(lo[0],lo[1],hi[0],hi[1]))
    repairs.append({'edge':name,'source_node_before':src,'target_node_before':dst,'old_xy':source['xy'],
        'node_xy':target['xy'],'horizontal_gap_m':float(np.linalg.norm(delta)),'old_height_m':source['z'],
        'target_height_m':target['z'],'taper_length_m':blend,'modified_edge_max_grade':e['max_grade'],
        'patch_bounds':[float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1])]})
for n in p['nodes']:n['edges']=[]
for i,e in enumerate(p['edges']):
    p['nodes'][e['a']]['edges'].append(i);p['nodes'][e['b']]['edges'].append(i)
used=[i for i,n in enumerate(p['nodes']) if n['edges']];mapping={v:i for i,v in enumerate(used)}
p['nodes']=[p['nodes'][i] for i in used]
for e in p['edges']:e['a']=mapping[e['a']];e['b']=mapping[e['b']]
newroad,newfull=roadshape(p['edges'])
new_area=newfull.difference(oldfull)
footprints=[Polygon(b['footprint']) for b in p['buildings']]
realpads=[Polygon(b['footprint_xy']) for b in p['real_buildings']]
realpaths=[LineString([b['access_start_xy'],b['access_end_xy']]).buffer(b.get('access_width_m',3)/2) for b in p['real_buildings']]
impacts=[]
for b,geom in zip(p['buildings'],footprints):
    area=geom.intersection(new_area).area
    if area>.01:impacts.append([b['name'],round(area,4)])
real_impacts=[b['instance_name'] for b,geom in zip(p['real_buildings'],realpads) if geom.intersects(new_area)]
path_impacts=[b['instance_name'] for b,geom in zip(p['real_buildings'],realpaths) if geom.intersects(new_area)]
print('ROAD_REPAIRS',json.dumps(repairs),flush=True)
print('ROAD_IMPACTS',json.dumps({'placeholder_intersections':impacts,'real_pads':real_impacts,'real_paths':path_impacts}),flush=True)
assert not real_impacts and not path_impacts,'New road would disturb user-provided buildings'

# Small placeholder buildings that encroach on new road geometry may be moved
# later in Blender; keep a precise list instead of deleting silently.
road_clearing=[name for name,area in impacts]
if road_clearing:
    p['buildings']=[b for b in p['buildings'] if b['name'] not in road_clearing]
    footprints=[Polygon(b['footprint']) for b in p['buildings']]

occupied={b['name']:Polygon(b['footprint']) for b in p['buildings']}
other=unary_union(list(occupied.values())+realpads+realpaths)
road_reserve=newfull.buffer(2.0)
cbd_boxes=[b for b in p['buildings'] if b['zone']=='CBD']
podiums=[]
shuffled=list(cbd_boxes);rng.shuffle(shuffled)
for b in shuffled:
    x,y=b['center'];sx,sy,_=b['size'];expand=rng.uniform(3,7)
    poly=box(x-sx/2-expand,y-sy/2-expand,x+sx/2+expand,y+sy/2+expand)
    if poly.intersects(road_reserve):continue
    if any(poly.buffer(1.5).intersects(q) for name,q in occupied.items() if name!=b['name']):continue
    if any(poly.buffer(1).intersects(q) for q in realpads+realpaths):continue
    if any(poly.buffer(1).intersects(Polygon(q['footprint'])) for q in podiums):continue
    podiums.append({'name':'CBD_Podium_Blockout_%03d'%len(podiums),'parent_tower':b['name'],
        'center':[x,y],'size':[sx+expand*2,sy+expand*2,rng.uniform(7,13)],'footprint':[list(xy) for xy in poly.exterior.coords]})
    if len(podiums)>=55:break

def rotated_rectangle(center,w,d,angle):
    c,s=math.cos(angle),math.sin(angle);a=np.array([c,s]);b=np.array([-s,c]);q=np.asarray(center)
    return Polygon([q-a*w/2-b*d/2,q+a*w/2-b*d/2,q+a*w/2+b*d/2,q-a*w/2+b*d/2])

# Place old-town street-front row blocks close to existing M18/M19 sidewalks.
street_blocks=[];new_reserved=[]
street_edges=[e for e in p['edges'] if e['name'] in ['M18_Oldtown_North','M19_Oldtown_South']]
rng.shuffle(street_edges)
for e in street_edges:
    line=LineString(np.asarray(e['points'])[:,:2])
    if line.length<35:continue
    for dist in np.arange(12,line.length-10,15.5):
        pt=line.interpolate(dist);x,y=pt.x,pt.y
        if not (-950<x<450 and 180<y<515):continue
        q0=line.interpolate(max(0,dist-3));q1=line.interpolate(min(line.length,dist+3))
        vec=np.array([q1.x-q0.x,q1.y-q0.y]);vec/=np.linalg.norm(vec);angle=math.atan2(vec[1],vec[0]);n=np.array([-vec[1],vec[0]])
        for side in [-1,1]:
            w=rng.uniform(12,15);d=rng.uniform(8.5,11.5);h=rng.uniform(8,15)
            center=np.array([x,y])+n*side*(e['width']/2+2+d/2);poly=rotated_rectangle(center,w,d,angle)
            if poly.intersects(road_reserve) or poly.buffer(2).intersects(other):continue
            if any(poly.buffer(1.5).intersects(q) for q in new_reserved):continue
            street_blocks.append({'name':'OLDTOWN_Arcade_Blockout_%03d'%len(street_blocks),'center':center.tolist(),'size':[w,d,h],
                'angle':angle,'footprint':[list(q) for q in poly.exterior.coords],'front_road':e['name']})
            new_reserved.append(poly)
            if len(street_blocks)>=48:break
        if len(street_blocks)>=48:break
    if len(street_blocks)>=48:break

# Additional modest housing around old-town assets, without blocking their
# foundations, paths, the road network or already-reserved shop frontage.
housing=[]
existing_union=unary_union([other,road_reserve]+new_reserved)
for _ in range(3000):
    x=rng.uniform(-210,130);y=rng.uniform(150,445)
    w=rng.uniform(15,22);d=rng.uniform(12,18);h=rng.uniform(12,25)
    poly=box(x-w/2,y-d/2,x+w/2,y+d/2)
    if poly.buffer(3).intersects(existing_union):continue
    housing.append({'name':'OLDTOWN_Housing_Blockout_%03d'%len(housing),'center':[x,y],'size':[w,d,h],
                    'footprint':[list(q) for q in poly.exterior.coords]})
    existing_union=unary_union([existing_union,poly.buffer(3)]);new_reserved.append(poly)
    if len(housing)>=34:break

# Select flat-ish port yard rectangles on the eastern island, close to docks and
# outside road/building setbacks. Their finished heights are sampled in Blender.
east=Polygon(p['coasts']['EAST'])
yards=[]
for attempt in range(6000):
    x=rng.uniform(900,1560);y=rng.uniform(-1000,-330)
    w,d=(60,40) if attempt%2 else (48,38)
    poly=box(x-w/2,y-d/2,x+w/2,y+d/2)
    if not east.buffer(-12).contains(poly) or poly.buffer(2).intersects(existing_union):continue
    if any(poly.buffer(30).intersects(Polygon(q['footprint'])) for q in yards):continue
    yards.append({'name':'PORT_Container_Yard_%02d'%len(yards),'center':[x,y],'size':[w,d],
                  'footprint':[list(q) for q in poly.exterior.coords]})
    existing_union=unary_union([existing_union,poly.buffer(4)])
    if len(yards)>=3:break

# Quiet lakeside low blocks are selected away from the lake edge and roads.
west=Polygon(p['coasts']['WEST']);lake=Polygon(p['lake']);lakebuild=[]
for _ in range(3000):
    x=rng.uniform(-1400,-520);y=rng.uniform(-950,-250)
    if not 45<lake.distance(Point(x,y))<190:continue
    w=rng.uniform(16,26);d=rng.uniform(12,20);h=rng.uniform(6,12)
    poly=box(x-w/2,y-d/2,x+w/2,y+d/2)
    if not west.buffer(-15).contains(poly) or poly.intersects(lake.buffer(35)) or poly.buffer(3).intersects(existing_union):continue
    lakebuild.append({'name':'WEST_Lakeside_Blockout_%02d'%len(lakebuild),'center':[x,y],'size':[w,d,h],
                      'footprint':[list(q) for q in poly.exterior.coords]})
    existing_union=unary_union([existing_union,poly.buffer(15)])
    if len(lakebuild)>=35:break

stats=p['stats'];stats['junctions']=sum(len(n['edges'])>=3 for n in p['nodes'])
stats['road_length_m']=sum(e['length'] for e in p['edges']);stats['maximum_road_grade']=max(e['max_grade'] for e in p['edges'])
stats['connected_components']=1;stats['road_junction_merges']=len(repairs)
plan={'repairs':repairs,'patch_bounds':[list(q.bounds) for q in patches],'road_clearing_placeholders':road_clearing,
      'cbd_podiums':podiums,'oldtown_arcade_blockouts':street_blocks,'oldtown_housing_blockouts':housing,
      'east_container_yards':yards,'west_lakeside_blockouts':lakebuild,
      'old_pavement':shapely.to_geojson(oldroad),'old_full_footprint':shapely.to_geojson(oldfull),
      'new_pavement':shapely.to_geojson(newroad),'new_full_footprint':shapely.to_geojson(newfull)}
(args.out/'redevelopment_plan.json').write_text(json.dumps(plan,separators=(',',':')))
(args.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')))
print('SCHEME_COUNTS',json.dumps({k:len(plan[k]) for k in ['repairs','road_clearing_placeholders','cbd_podiums','oldtown_arcade_blockouts','oldtown_housing_blockouts','east_container_yards','west_lakeside_blockouts']}),flush=True)
