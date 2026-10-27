"""Check the updated road graph and planned blockout footprints."""
import argparse,json,math
from pathlib import Path
import numpy as np,shapely
from shapely.geometry import Polygon,LineString
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--scheme',type=Path,required=True)
ap.add_argument('--districts',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
p=json.loads(a.plan.read_text());s=json.loads(a.scheme.read_text());d=json.loads(a.districts.read_text())
nodes=p['nodes'];edges=p['edges'];seen=set();parts=[]
for i,n in enumerate(nodes):
    if i in seen:continue
    stack=[i];part=set()
    while stack:
        j=stack.pop()
        if j in seen:continue
        seen.add(j);part.add(j)
        for ei in nodes[j]['edges']:
            e=edges[ei];stack.append(e['b'] if e['a']==j else e['a'])
    parts.append(part)
assert len(parts)==1
maximum=0;endpoint_error=0
for i,e in enumerate(edges):
    q=np.asarray(e['points']);length=np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1)
    maximum=max(maximum,float(np.max(np.abs(np.diff(q[:,2]))/length)))
    endpoint_error=max(endpoint_error,abs(q[0,2]-nodes[e['a']]['z']),abs(q[-1,2]-nodes[e['b']]['z']))
    assert i in nodes[e['a']]['edges'] and i in nodes[e['b']]['edges']
assert maximum<=.085001 and endpoint_error<.0001,(maximum,endpoint_error)
targets=[]
for fix in s['repairs']:
    i=min(range(len(nodes)),key=lambda k:math.dist(nodes[k]['xy'],fix['node_xy']))
    names=[edges[e]['name'] for e in nodes[i]['edges']]
    assert math.dist(nodes[i]['xy'],fix['node_xy'])<.001
    assert names.count(fix['edge'])>=2, (fix['edge'],names)
    targets.append({'edge':fix['edge'],'node':i,'degree':len(names),'incident_edges':names})
road=shapely.from_geojson(s['new_pavement']);full=shapely.from_geojson(s['new_full_footprint']);walk=full.difference(road)
assert road.is_valid and full.is_valid and len([g for g in shapely.get_parts(road) if g.area>.1])==1
assert walk.intersection(road).area<.001
boxes=p['buildings'];polys=[Polygon(b['footprint']) for b in boxes]
pads=[Polygon(b['footprint_xy']) for b in p['real_buildings']]
all_geom=polys+pads;tree=shapely.STRtree(all_geom)
new=[i for i,b in enumerate(boxes) if b['name'].startswith(('OLDTOWN_Arcade_Blockout_','OLDTOWN_Housing_Blockout_','WEST_Lakeside_Blockout_','UNIVERSITY_Teaching_','CIVIC_City_','CULTURE_Public_'))]
overlap=[];road_hits=[]
for i in new:
    poly=polys[i]
    if poly.intersection(full).area>1e-5:road_hits.append(boxes[i]['name'])
    for j in tree.query(poly,predicate='intersects'):
        if i==j:continue
        if poly.intersection(all_geom[int(j)]).area>1e-5:overlap.append(boxes[i]['name']);break
assert not overlap and not road_hits,(overlap,road_hits)
for podium in d['cbd_podiums']:
    poly=Polygon(podium['footprint'])
    assert not poly.intersects(full)
    for i in tree.query(poly,predicate='intersects'):
        if i<len(boxes) and boxes[int(i)]['name']==podium['parent_tower']:continue
        assert poly.intersection(all_geom[int(i)]).area<1e-5,(podium['name'],int(i))
for yard in d['east_container_yards']:
    poly=Polygon(yard['footprint'])
    assert not poly.intersects(full)
    assert not any(poly.intersection(all_geom[int(i)]).area>1e-5 for i in tree.query(poly,predicate='intersects'))
access_checks=[]
for access in p.get('port_service_access',[]):
    matched=[e for e in edges if e['name']==access['service_edge']]
    assert len(matched)==1 and len(nodes[matched[0]['b']]['edges'])>=3
    yard=next(y for y in d['east_container_yards'] if y['name']==access['yard'])
    assert Polygon(yard['footprint']).covers(shapely.Point(access['start_xy']))
    corridor=LineString([access['start_xy'],access['end_xy']]).buffer(access['drive_width_m']/2,cap_style='flat')
    hits=[int(i) for i in tree.query(corridor,predicate='intersects') if corridor.intersection(all_geom[int(i)]).area>1e-5]
    assert not hits,(access['yard'],hits)
    assert access['walk_end_max_lip_m']<.02 and access['road_end_max_lip_m']<.02
    access_checks.append({'yard':access['yard'],'edge':access['service_edge'],'road_connection_degree':len(nodes[matched[0]['b']]['edges']),'building_overlaps':len(hits)})
assert len(access_checks)==len(d['east_container_yards'])
out={'graph_components':len(parts),'nodes':len(nodes),'edges':len(edges),'junctions':sum(len(n['edges'])>=3 for n in nodes),
 'remaining_dead_ends':sum(len(n['edges'])==1 for n in nodes),'repaired_junctions':targets,
 'max_centerline_grade':maximum,'max_endpoint_height_error_m':endpoint_error,
 'pavement_components':1,'pavement_sidewalk_overlap_m2':walk.intersection(road).area,
 'new_buildings_checked':len(new),'new_building_overlaps':len(overlap),'new_building_road_overlaps':len(road_hits),
 'podiums_checked':len(d['cbd_podiums']),'port_yards_checked':len(d['east_container_yards']),
 'port_service_access_checks':access_checks,'validation_passed':True}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
