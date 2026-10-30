"""Adapt S05 street hierarchy to existing mainland and western neighborhoods."""
from pathlib import Path
import sys,json,math,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'))
import numpy as np,shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from scipy.interpolate import PchipInterpolator
p=json.load(open(R/'baseline/city_plan.json'));cat={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))}
removed=[b for b in p['buildings'] if b['region']=='WEST' and b.get('block_id')==17];rn={b['name'] for b in removed}
fixed=[b for b in p['buildings'] if b['name'] not in rn]+p['real_buildings'];fixedpoly=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in fixed]);lands={k:Polygon(v) for k,v in p['coasts'].items()};reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
oldroad=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in p['edges']])
def smooth(points):
 a=np.array(points,float);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(a,axis=0),axis=1))];n=np.linspace(0,s[-1],int(s[-1]/2)+2);return LineString(np.c_[PchipInterpolator(s,a[:,0])(n),PchipInterpolator(s,a[:,1])(n)])
roads=[]
def road(name,reg,pts,carriage,walk,snap_start=True):
 pts=[list(q) for q in pts]
 for ix in ([0,-1] if snap_start else [-1]):
  q=Point(pts[ix]);line=min([LineString(np.array(e['points'])[:,:2]) for e in p['edges'] if e['region']==reg],key=lambda x:x.distance(q));assert line.distance(q)<25,(name,pts[ix]);pts[ix]=list(line.interpolate(line.project(q)).coords[0])
 line=smooth(pts);roads.append(dict(name=name,region=reg,points=list(line.coords),carriage_width=carriage,sidewalk_width=walk,width=carriage+2*walk,layer='GROUND_V20',bridge=False,display_name_zh=name))
 return line
main=road('V20_Newtown_Crescent','MAIN',[[600,591],[640,603],[680,611],[730,611],[775,601],[820,589],[852,593],[884,607],[904,630],[912,655]],7,2)
join=main.interpolate(main.project(Point(703,611)));road('V20_Newtown_Garden_Link','MAIN',[join.coords[0],[703,631],[703,655]],5,1.6,False)
west=road('V20_West_Market_Bend','WEST',[[-1000,-929],[-974,-929],[-945,-944],[-915,-945],[-882,-932],[-852,-929],[-800,-929]],6.4,1.8)
wj=west.interpolate(west.project(Point(-908,-944)));road('V20_West_Garden_Link','WEST',[wj.coords[0],[-902,-916],[-902,-888],[-900,-870]],5,1.5,False)
newshape=unary_union([LineString(r['points']).buffer(r['width']/2,join_style=2) for r in roads]);roadshape=oldroad.union(newshape)
assert newshape.intersection(fixedpoly).area<.001,('road intersects existing building',newshape.intersection(fixedpoly).area)
placements=[];rejections=[]
def district(q):
 if q[0]<-430 and q[1]<-300:return 9 if q[0]<-950 else 10
 return 4 if q[1]<620 else 8
def source_front(aid):
 return np.array([0,1]) if aid in ['S02-B03','S02-B05'] else np.array([1,0]) if aid in ['S06-B04','S06-B05','S06-B06'] else np.array([0,-1])
def place(aid,center,normal,scale,group,reg):
 a=cat[aid];sf=source_front(aid);angle=math.atan2(normal[1],normal[0])-math.atan2(sf[1],sf[0]);rot=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]);w,d,h=np.array(a['normalized_size_m'])*scale
 delta=np.array([[-w/2,-d/2],[w/2,-d/2],[w/2,d/2],[-w/2,d/2]])@rot.T;center=np.array(center);poly=Polygon(delta+center)
 if not lands[reg].buffer(-.1).covers(poly) or poly.intersects(roadshape.buffer(.15)) or poly.intersects(fixedpoly.buffer(.45)) or poly.intersects(reserve.buffer(.1)):return None
 if any(poly.distance(Polygon(b['footprint_xy']))<1.15 for b in placements):return None
 ix=1+sum(b.get('asset_id')==aid for b in p['real_buildings']+placements);iid=f'{aid}-I{ix:02}'
 rec=dict(name=iid,instance_id=iid,instance_name=iid,asset_id=aid,display_name_zh=a['display_name_zh'],file=a['file'],source_filename=a['source_filename'],source_node_name=a['source_node_name'],source_sha256=a['source_sha256'],asset_sha256=a['sha256'],center=center.tolist(),rotation_deg=math.degrees(angle),scale=scale,uniform_scale=scale,height=float(h),footprint_xy=list(poly.exterior.coords),outward=np.asarray(normal).tolist(),region=reg,zone='VILLAGE' if reg=='WEST' else 'NEW_TOWN',district_id=district(center),group=group,layout_group=group,building_count_units=1,added_in_version='v20',replaces=[])
 placements.append(rec);return rec
def front_row(line,side,sequence,group,reg,default_scale):
 distance=23.;i=0
 while distance<line.length-22:
  aid=sequence[i%len(sequence)];scale=default_scale*(1.0 if i%3 else .97);a=cat[aid];sf=source_front(aid);along=a['normalized_size_m'][0 if sf[1] else 1]*scale;depth=a['normalized_size_m'][1 if sf[1] else 0]*scale
  q=np.array(line.interpolate(distance).coords[0]);t=np.array(line.interpolate(min(line.length,distance+1)).coords[0])-np.array(line.interpolate(max(0,distance-1)).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])*side;c=q+n*(5.5 if reg=='MAIN' else 5.0)+n*(depth/2+.85)
  b=place(aid,c,-n,scale,group,reg)
  if not b:rejections.append(dict(asset=aid,station=distance,group=group));distance+=4
  else:distance+=along+2.0
  i+=1
front_row(main,1,['S02-B01','S06-B03','S02-B02','S04-B10','S06-B06','S04-B04','S02-B03'],'NT_CRESCENT_SHOPFRONTS','MAIN',1)
front_row(main,-1,['S06-B04','S02-B03','S04-B08','S02-B02','S06-B03','S04-B06','S02-B01'],'NT_CRESCENT_SHOPFRONTS','MAIN',1)
front_row(west,1,['S02-B02','S02-B03','S04-B10','S02-B01','S04-B08','S02-B04'],'WEST_MARKET_STREET','WEST',.86)
front_row(west,-1,['S02-B05','S04-B06','S02-B03','S02-B02','S04-B10','S02-B05'],'WEST_MARKET_STREET','WEST',.88)
for aid,initial,normal,scale in [('S03-B01',[659,721],[0,-1],1),('S03-B06',[662,771],[1,0],.78),('S04-B04',[649,682],[0,-1],1),('S04-B05',[681,681],[0,-1],.9)]:
 options=sorted([(dx,dy) for dx in range(-32,33,2) for dy in range(-26,27,2)],key=lambda q:q[0]*q[0]+q[1]*q[1]);placed=None
 for dx,dy in options:
  placed=place(aid,[initial[0]+dx,initial[1]+dy],normal,scale,'NT_STEPPED_CAMPUS','MAIN')
  if placed:break
 assert placed,(aid,initial)
 print('CAMPUS',aid,placed['center'],flush=True)
# Each original placeholder has a traceable nearest replacement in this block.
for b in removed:
 nearest=min([r for r in placements if r['region']=='WEST'],key=lambda r:Point(r['center']).distance(Point(b['center'])));nearest['replaces'].append(b['name'])
groups=[dict(id='NT_CRESCENT_SHOPFRONTS',name_zh='新城弧线生活街',region='MAIN',focus=[763,606],strategy='弯曲次干路串联短街面，错位T字路口连接北侧主路，街角留口袋绿地'),dict(id='NT_STEPPED_CAMPUS',name_zh='新城错层商务组团',region='MAIN',focus=[660,735],strategy='低层服务楼靠近主街、较高建筑后退布置，绿地与步道贯通'),dict(id='WEST_MARKET_STREET',name_zh='西岛曲街生活区',region='WEST',focus=[-906,-934],strategy='S形生活街连接既有路网，商住楼与坡顶住宅交错，北侧支路形成非等距街坊')]
out=dict(version='v20',baseline_commit='e9cd715cb39763a01c40a19255f6992a40ef2f79',changed_district_ids=[4,8,9,10],inspiration='S05 city (1)(1).glb: curved arterial/secondary hierarchy, offset T junctions, corner planting pockets, varied block fronts; adapt to current coordinates and hills',new_roads=roads,removed_placeholder_lots=removed,placements=placements,groups=groups,city_building_units=p['stats']['buildings']-len(removed)+len(placements))
(R/'layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('LAYOUT',len(placements),'new',len(removed),'removed',out['city_building_units'],'total',collections.Counter(r['group'] for r in placements));print('TYPES',collections.Counter(r['asset_id'] for r in placements))
