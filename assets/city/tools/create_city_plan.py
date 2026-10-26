"""Deterministic 4 km city blockout plan. Run with numpy/scipy/shapely installed.

Coordinates are digitized from the user's supplied three-island concept image.
The image is a planning reference, not a cadastral survey. Units are metres.
"""
from pathlib import Path
import argparse, json, math, random, sys, heapq
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import Delaunay, cKDTree
try:
    import shapely
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'runtime/py'))
    import shapely
from shapely.geometry import Polygon, LineString, Point, MultiLineString, MultiPoint, box
from shapely.ops import unary_union, nearest_points, polygonize, triangulate
from shapely import contains_xy, intersects_xy

SCALE=4.6
RNG=random.Random(13026)
ROOT=Path(__file__).resolve().parents[1]

def xy(p): return ((p[0]-440)*SCALE,(450-p[1])*SCALE)
def px(p): return (p[0]/SCALE+440,450-p[1]/SCALE)
def smoothstep(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def curve(points,closed=False,step=10):
    a=np.array([xy(p) for p in points],float)
    if closed and np.linalg.norm(a[0]-a[-1])>1e-6:a=np.vstack([a,a[0]])
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(a,axis=0),axis=1))]
    cs=CubicSpline(d,a,bc_type='periodic' if closed else 'natural')
    return cs(np.linspace(0,d[-1],max(2,int(d[-1]/step)+1)))

COASTS={
'MAIN':[(58,309),(63,282),(76,253),(111,228),(137,208),(165,176),(184,144),(215,129),(241,99),(253,71),(286,61),(308,35),(342,17),(368,23),(383,47),(372,65),(353,77),(358,97),(386,110),(422,116),(457,109),(483,103),(510,111),(531,117),(553,106),(572,83),(591,78),(613,85),(632,106),(660,122),(679,140),(687,167),(710,174),(725,196),(739,218),(748,240),(765,258),(775,274),(797,285),(815,304),(830,327),(843,345),(834,364),(817,380),(807,403),(791,423),(774,440),(751,451),(730,449),(715,434),(691,431),(666,445),(641,440),(616,432),(589,430),(559,439),(533,453),(510,466),(489,474),(465,475),(441,462),(420,449),(397,442),(368,436),(340,427),(314,416),(288,401),(265,389),(238,378),(214,376),(191,367),(170,354),(154,344),(132,339),(108,342),(85,330),(65,324)],
'WEST':[(34,511),(49,482),(75,459),(103,453),(134,461),(162,471),(187,473),(213,481),(238,496),(259,513),(278,528),(300,543),(326,550),(349,561),(368,579),(385,599),(406,619),(423,638),(417,658),(401,673),(393,696),(382,714),(367,733),(350,753),(325,766),(299,776),(274,783),(247,798),(218,805),(190,801),(165,791),(140,784),(118,783),(91,773),(68,755),(54,730),(43,705),(34,677),(25,651),(22,619),(20,591),(23,562),(27,538)],
'EAST':[(493,633),(503,601),(523,579),(546,558),(563,535),(586,520),(610,519),(629,526),(650,516),(675,502),(699,503),(723,515),(746,533),(756,554),(776,566),(799,580),(814,603),(822,632),(821,658),(830,686),(841,712),(839,735),(846,760),(841,783),(824,800),(803,814),(776,825),(750,841),(718,852),(691,848),(662,841),(640,848),(612,844),(588,830),(564,817),(539,795),(521,772),(511,747),(500,722),(494,692),(486,666)]}
ISLANDS={k:Polygon(curve(v,True,9)).buffer(0) for k,v in COASTS.items()}
lake=Polygon(curve([(192,550),(221,537),(251,547),(269,566),(276,588),(263,612),(246,631),(217,637),(193,623),(180,604),(179,579)],True,7))
LAND=unary_union(list(ISLANDS.values()))
SAFE=LAND.buffer(-17).difference(lake.buffer(13))

def raw_height(x,y):
    a=np.asarray(x);b=np.asarray(y);u=a/SCALE+440;v=450-b/SCALE
    def g(cx,cy,sx,sy,h):return h*np.exp(-((u-cx)/sx)**2-((v-cy)/sy)**2)
    h=8+g(292,101,88,74,142)+g(349,47,36,39,54)+g(157,271,76,78,34)+g(653,177,64,69,52)+g(465,214,170,122,16)
    h+=g(105,525,68,83,118)+g(319,607,60,72,55)+g(115,674,78,68,31)+g(548,676,58,86,57)+g(742,752,75,77,12)
    h+=1.1*np.sin(a/127)*np.sin(b/143)+0.5*np.sin(a/41+b/69)
    points=shapely.points(a,b)
    d=shapely.distance(points,LAND.boundary)
    h=3.0+(h-3.0)*smoothstep(d/95)
    h=np.where(contains_xy(LAND,a,b),h,-5)
    # The west-island freshwater lake has one level, including its shore shelf.
    dl=shapely.distance(points,lake)
    w=1-smoothstep(dl/80)
    h=h*(1-w)+22*w
    return h

ROUTES=[]
def route(name,pts,width=12,region='MAIN',closed=False,bridge=False):
    co=curve(pts,closed,9)
    line=LineString(co)
    geom=line if bridge else line.intersection(SAFE)
    parts=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
    for q in parts:
        if q.geom_type=='LineString' and q.length>14:
            ROUTES.append(dict(name=name,width=width,region=region,bridge=bridge,line=q,profile_line=line if bridge else None))

def roads():
    route('M01_Coastal_Ring',[(110,307),(132,269),(175,215),(216,181),(262,151),(310,137),(353,137),(399,148),(447,158),(492,151),(539,130),(581,119),(621,134),(652,162),(684,193),(719,224),(744,264),(769,292),(795,314),(814,345),(799,378),(775,406),(745,427),(710,426),(682,421),(656,428),(630,417),(601,412),(570,418),(538,433),(504,450),(477,455),(446,447),(414,433),(375,420),(337,409),(296,392),(252,379),(209,365),(169,350),(133,329)],24,closed=True)
    route('M02_Civic_East_West',[(120,293),(173,284),(224,288),(276,300),(329,311),(382,321),(434,329),(478,334),(529,335),(580,339),(632,338),(684,331),(735,317),(787,306)],24)
    route('M03_Central_North_South',[(472,146),(472,179),(476,218),(478,258),(479,296),(478,334),(478,374),(477,414),(477,455)],24)
    route('M04_CBD_North_Avenue',[(286,187),(330,185),(374,181),(420,180),(472,179),(521,177),(569,177),(614,183),(652,197),(690,214)],24)
    route('M05_University_Connector',[(195,218),(239,223),(280,225),(323,223),(365,218),(418,218),(476,218),(525,218),(572,220),(620,227),(672,235),(721,248)],12)
    route('M06_CBD_Market_Street',[(189,253),(231,259),(280,262),(327,260),(372,258),(423,258),(478,258),(527,259),(572,261),(617,267),(665,275),(738,286)],12)
    route('M07_Southern_CBD_Avenue',[(273,300),(327,296),(375,294),(426,295),(479,296),(527,296),(572,300),(618,306),(669,309),(735,317)],12)
    for x in [355,399,438,520,562,603]:
        route(f'M_CBD_Cross_{x}',[(x-4,146),(x-2,180),(x,219),(x+1,258),(x+3,296),(x+3,335)],12)
    route('M08_West_College_Avenue',[(233,171),(239,223),(231,259),(224,288),(218,330),(209,365)],12)
    route('M09_West_Residential',[(282,149),(283,189),(280,225),(280,262),(276,300),(267,338),(252,379)],12)
    route('M10_West_Spines',[(172,219),(180,252),(173,284),(164,321),(169,350)],12)
    route('M11_College_Walk',[(203,191),(239,191),(283,189),(330,185)],12)
    route('M12_Residential_Link',[(140,311),(184,315),(218,330),(267,338),(303,352)],12)
    route('M13_Upper_Hill_Road',[(216,181),(224,152),(249,134),(276,119),(300,99),(321,91),(331,107),(309,123),(310,137)],12)
    route('M14_North_Park_Switchbacks',[(249,134),(244,112),(262,91),(284,81),(307,69),(331,55),(351,47),(356,62),(340,77),(321,91)],12)
    route('M15_North_Ridge_Return',[(353,137),(355,125),(373,128),(388,137),(399,148)],12)
    route('M16_Admin_Boulevard',[(581,119),(597,146),(614,183),(620,227),(617,267),(618,306),(632,338),(630,373),(630,417)],24)
    for x in [652,691]:
        route(f'M_Admin_Link_{x}',[(x-14,150),(x-6,188),(x,225),(x+2,266),(x+7,304),(x+7,328)],12)
    route('M17_Admin_Cross',[(597,146),(629,155),(669,174)],12)
    route('M18_Oldtown_North',[(303,352),(341,353),(380,356),(420,358),(478,358),(519,358),(560,358),(600,361),(630,373),(681,380),(733,375),(799,361)],12)
    route('M19_Oldtown_South',[(294,384),(334,380),(372,382),(412,384),(448,385),(478,383),(517,382),(554,382),(593,385),(630,393),(682,400),(739,398),(785,394)],12)
    for x in [331,369,407,444,518,556,595]:
        route(f'M_Oldtown_Block_{x}',[(x+1,320),(x+5,351),(x+3,381),(x+1,414)],12)
    for x in [675,717,758]:
        route(f'M_Cultural_{x}',[(x,333),(x+5,365),(x+7,400),(x-1,428)],12)
    route('M20_East_Cape_Loop',[(733,375),(772,364),(793,344),(803,329),(814,345)],12)
    # West island: a coastal ring, a lake circuit, village links and real hill bends.
    route('W01_Coastal_Ring',[(60,521),(84,492),(116,491),(151,503),(184,521),(214,533),(248,550),(281,562),(315,575),(343,590),(369,615),(387,638),(386,669),(367,700),(344,727),(313,747),(280,761),(247,777),(211,781),(178,769),(143,758),(108,753),(80,734),(65,707),(54,675),(46,641),(45,607),(48,573)],24,'WEST',True)
    route('W02_Lake_Circuit',[(152,568),(166,544),(193,529),(221,525),(252,539),(279,558),(292,586),(285,614),(265,640),(234,653),(202,650),(176,636),(160,610)],12,'WEST',True)
    route('W03_Lake_South_Avenue',[(54,675),(100,667),(144,657),(176,636),(202,650),(234,653),(278,655),(327,651),(387,638)],24,'WEST')
    route('W04_Rural_Main_Street',[(84,492),(96,534),(101,578),(100,622),(100,667),(109,714),(108,753)],12,'WEST')
    route('W05_Eastern_Lakeside',[(184,521),(193,529),(221,525),(226,531),(252,539),(281,562),(315,575)],12,'WEST')
    route('W06_South_Resort_Avenue',[(80,734),(120,714),(162,707),(204,712),(246,718),(290,718),(344,727)],12,'WEST')
    route('W07_Village_North',[(58,630),(100,622),(135,613),(160,610)],12,'WEST')
    route('W08_Farm_Lane',[(65,707),(109,691),(148,685),(190,683),(234,685),(278,685),(320,689),(367,700)],12,'WEST')
    for x in [141,181,224,266,307]:
        route(f'W_South_Link_{x}',[(x-4,651),(x+3,684),(x+2,714),(x+2,757)],12,'WEST')
    route('W09_Hill_Serpentine',[(60,521),(57,547),(76,559),(94,549),(116,535),(138,540),(144,558),(126,572),(101,578)],12,'WEST')
    route('W10_Hill_Upper_Loop',[(116,491),(119,514),(111,530),(96,534),(78,522),(84,508),(102,505),(119,514)],12,'WEST')
    route('W11_East_Hills_Road',[(292,586),(316,597),(332,619),(327,651),(315,671),(320,689)],12,'WEST')
    # East island: port access, parallel warehouse streets and a lower urban grid.
    route('E01_Industrial_Ring',[(531,622),(554,592),(584,567),(614,550),(647,548),(679,536),(706,542),(732,561),(758,588),(788,612),(799,645),(802,677),(812,710),(815,748),(803,777),(774,797),(738,819),(703,829),(666,822),(633,825),(603,813),(574,795),(548,771),(534,740),(524,705),(519,671)],24,'EAST',True)
    route('E02_Port_Distributor',[(554,592),(587,605),(623,618),(657,633),(693,650),(730,668),(767,685),(805,698)],24,'EAST')
    route('E03_Southern_Logistics',[(534,740),(566,727),(600,717),(637,708),(675,708),(710,720),(748,741),(784,755),(815,748)],24,'EAST')
    route('E04_West_Urban_Avenue',[(584,567),(578,605),(566,644),(556,681),(558,719),(566,760),(574,795)],12,'EAST')
    route('E05_East_Freight_Avenue',[(679,536),(673,573),(657,610),(642,649),(632,682),(637,708),(654,752),(666,789),(666,822)],24,'EAST')
    route('E06_Dock_Access',[(614,550),(627,569),(651,579),(679,581),(706,571),(732,561)],12,'EAST')
    route('E07_Warehouse_North',[(578,605),(615,588),(651,579),(679,581),(714,600),(752,617),(788,612)],12,'EAST')
    route('E08_Warehouse_Middle',[(531,622),(566,644),(605,660),(642,675),(678,687),(716,703),(754,718),(812,710)],12,'EAST')
    route('E09_Warehouse_South',[(519,671),(556,681),(596,693),(632,701),(675,708)],12,'EAST')
    for a,b in [(603,624),(713,731),(753,770)]:
        route(f'E_Freight_Cross_{a}',[(a,578),(a-8,611),(a-19,643),(a-28,677),(a-35,709)],12,'EAST')
    route('E10_Residential_Cross',[(526,701),(557,719),(590,744),(622,768),(654,785),(692,791),(732,791),(774,797)],12,'EAST')
    route('E11_South_Cross',[(548,771),(586,771),(622,768),(657,760),(692,752),(724,760),(749,780),(758,807)],12,'EAST')
    for x in [591,626,698,737,775]:
        route(f'E_South_Link_{x}',[(x-8,724),(x-4,751),(x,781),(x+3,817)],12,'EAST')
    route('E12_Port_Spur_A',[(673,573),(682,549),(684,521)],12,'EAST')
    route('E13_Port_Spur_B',[(714,600),(737,590),(759,583)],12,'EAST')
    route('E14_West_Hill_Serpentine',[(519,671),(532,650),(546,657),(541,680),(529,697),(534,720),(558,719)],12,'EAST')
    # All four bridge corridors are part of the same connected road graph.
    route('B01_Western_Bridge',[(290,349),(279,386),(260,437),(241,490),(226,531)],24,'BRIDGES',bridge=True)
    route('B02_Southern_Bridge',[(477,414),(478,466),(479,535),(480,603),(480,643),(510,660),(548,676),(556,681)],24,'BRIDGES',bridge=True)
    route('B03_Eastern_Bridge',[(624,370),(639,419),(653,462),(676,528),(692,567),(706,571)],24,'BRIDGES',bridge=True)
    route('B04_West_East_Link',[(327,651),(369,636),(408,637),(448,641),(480,643)],24,'BRIDGES',bridge=True)

def main(out):
    out.mkdir(parents=True,exist_ok=True);roads()
    # Snap close road termini onto the adjoining corridor before noding the graph.
    for i,r in enumerate(ROUTES):
        cs=list(r['line'].coords)
        if np.linalg.norm(np.array(cs[0])-cs[-1])<1:continue
        for k in [0,-1]:
            p=Point(cs[k]);candidates=[]
            for j,q in enumerate(ROUTES):
                if i==j:continue
                d=p.distance(q['line'])
                if d<46:candidates.append((d,j))
            if candidates:
                d,j=min(candidates);cs[k]=tuple(nearest_points(p,ROUTES[j]['line'])[1].coords[0])
        r['line']=LineString(cs)
    # Coalesce nearly coincident corridors before graph noding. In particular,
    # bridge approaches replace the overlapping pieces of the coastal streets;
    # they cannot remain two independent roads a few metres apart.
    accepted=[]
    for r in sorted(ROUTES,key=lambda r:(not r['bridge'],-r['width'])):
        existing=unary_union([q['line'] for q in accepted]) if accepted else None
        occupied=unary_union([q['line'].buffer((q['width']+r['width'])/2+.5,cap_style=2,join_style=2) for q in accepted]) if accepted else None
        pieces=r['line'].difference(occupied) if occupied is not None else r['line']
        for piece in list(pieces.geoms) if hasattr(pieces,'geoms') else [pieces]:
            if piece.geom_type!='LineString' or piece.length<15:continue
            coords=list(piece.coords)
            if existing is not None:
                for end in [0,-1]:
                    p=Point(coords[end]);near=nearest_points(p,existing)[1]
                    if p.distance(near)<(max(q['width'] for q in accepted)+r['width'])/2+1.2:coords[end]=tuple(near.coords[0])
            accepted.append(r|{'line':LineString(coords)})
    ROUTES[:]=accepted
    for r in ROUTES:
        coords=list(r['line'].coords)
        for end in [0,-1]:
            point=Point(coords[end]);others=[q['line'] for q in ROUTES if q['name']!=r['name']]
            if others:
                nearest=nearest_points(point,unary_union(others))[1]
                if point.distance(nearest)<29:coords[end]=tuple(nearest.coords[0])
        r['line']=LineString(coords)
    termini=MultiPoint([p for r in ROUTES for p in [r['line'].coords[0],r['line'].coords[-1]]])
    for r in ROUTES:r['line']=shapely.snap(r['line'],termini,.12)
    union=unary_union([r['line'] for r in ROUTES])
    nodes=[];idx={};edges=[]
    def node(p):
        key=tuple(round(x,3) for x in p)
        if key not in idx:idx[key]=len(nodes);nodes.append({'xy':list(p),'edges':[]})
        return idx[key]
    lines=list(union.geoms) if hasattr(union,'geoms') else [union]
    for line in lines:
        if line.length<0.6:continue
        center=line.interpolate(.5,normalized=True)
        candidates=sorted(ROUTES,key=lambda r:r['line'].distance(center))
        r=candidates[0]
        if len(candidates)>1 and candidates[1]['line'].distance(center)<.1:
            r=max(candidates[:2],key=lambda q:q['width'])
        a=node(line.coords[0]);b=node(line.coords[-1]);ei=len(edges)
        edges.append(dict(a=a,b=b,name=r['name'],region=r['region'],width=r['width'],bridge=r['bridge'],line=line))
        nodes[a]['edges'].append(ei);nodes[b]['edges'].append(ei)
    # Collapse sub-lane-sized numerical slivers at coincident route intersections.
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for e in edges:
        if e['line'].length<14:parent[root(e['a'])]=root(e['b'])
    groups={}
    for i,n in enumerate(nodes):groups.setdefault(root(i),[]).append(i)
    remap={};newnodes=[]
    for group in groups.values():
        p=np.mean([nodes[i]['xy'] for i in group],axis=0).tolist();ni=len(newnodes)
        newnodes.append({'xy':p,'edges':[]})
        for i in group:remap[i]=ni
    newedges=[]
    for e in edges:
        a,b=remap[e['a']],remap[e['b']]
        if a==b:continue
        pts=np.array(e['line'].coords);start=np.array(newnodes[a]['xy']);end=np.array(newnodes[b]['xy'])
        keep=(np.linalg.norm(pts-start,axis=1)>4)&(np.linalg.norm(pts-end,axis=1)>4)
        e['line']=LineString(np.vstack([start,pts[keep][1:-1] if len(pts[keep])>2 else np.empty((0,2)),end]));e['a']=a;e['b']=b
        ni=len(newedges);newedges.append(e);newnodes[a]['edges'].append(ni);newnodes[b]['edges'].append(ni)
    nodes,edges=newnodes,newedges
    # One global graph also supplies elevation constraints across all junctions.
    all_xy=[n['xy'] for n in nodes];shared_n=len(nodes);links=[];edge_indices=[];desired=[]
    for ei,e in enumerate(edges):
        n=max(2,int(e['line'].length/6)+1);co=np.array([e['line'].interpolate(d).coords[0] for d in np.linspace(0,e['line'].length,n)])
        ids=[e['a']]
        for p in co[1:-1]:ids.append(len(all_xy));all_xy.append(p.tolist())
        ids.append(e['b']);edge_indices.append(ids)
        for a,b in zip(ids[:-1],ids[1:]):links.append((a,b,float(np.linalg.norm(np.array(all_xy[a])-all_xy[b]))))
    arr=np.array(all_xy);h=raw_height(arr[:,0],arr[:,1]);raw=h.copy()
    # Bridge profiles rise over 200 m approaches to a 28 m navigation clearance.
    for ei,e in enumerate(edges):
        if not e['bridge']:continue
        r=next(r for r in ROUTES if r['name']==e['name']);line=r['profile_line'] or r['line'];ids=np.array(edge_indices[ei]);p=arr[ids]
        ss=np.array([line.project(Point(q)) for q in p])
        start_land=LAND.contains(Point(line.coords[0]));end_land=LAND.contains(Point(line.coords[-1]))
        fade=np.minimum(smoothstep(ss/220) if start_land else np.ones(len(ss)),smoothstep((line.length-ss)/220) if end_land else np.ones(len(ss)))
        hz=raw_height(p[:,0],p[:,1]);hz=np.where(contains_xy(LAND,p[:,0],p[:,1]),hz,8)
        target=28+1.5*np.sin(ss/line.length*np.pi)
        bh=hz*(1-fade)+target*fade;h[ids]=np.maximum(h[ids],bh)
    # Average every ordinary intersection onto one small flat junction apron.
    for ni,n in enumerate(nodes):
        n['radius']=min(20,max((edges[e]['width'] for e in n['edges']),default=12)*.58+1.2)
    # Multi-source Dijkstra computes the exact 8.5%-Lipschitz lower envelope.
    # Unlike a fixed number of averaging iterations, this guarantees consistent
    # shared endpoints even on a long sequence of mountain-road samples.
    adjacency=[[] for _ in h]
    for a,b,length in links:adjacency[a].append((b,.085*length));adjacency[b].append((a,.085*length))
    heap=[(float(z),i) for i,z in enumerate(h)];heapq.heapify(heap)
    while heap:
        z,i=heapq.heappop(heap)
        if z>h[i]+1e-9:continue
        for j,cost in adjacency[i]:
            candidate=z+cost
            if candidate<h[j]-1e-9:h[j]=candidate;heapq.heappush(heap,(candidate,j))
    # Shared junction height and gentle vertical easing at the ends of every edge.
    sample_xy=[];sample_h=[];sample_w=[];sample_bridge=[];edge_export=[]
    for ei,e in enumerate(edges):
        ids=np.array(edge_indices[ei]);p=arr[ids];z=h[ids].copy();ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        # Limit local grade after vertical easing to < 10.5% (includes junction transitions).
        for end,ni in [(0,e['a']),(-1,e['b'])]:
            rr=nodes[ni]['radius']
            if rr>0:
                dist=ds if end==0 else ds[-1]-ds
                w=1-smoothstep(np.maximum(dist-rr,0)/45)
                z=z*(1-w)+h[ni]*w
        z[0]=h[e['a']];z[-1]=h[e['b']]
        lower=np.maximum(z[0]-.102*ds,z[-1]-.102*(ds[-1]-ds))
        upper=np.minimum(z[0]+.102*ds,z[-1]+.102*(ds[-1]-ds))
        z=np.clip(z,lower,upper)
        z=np.minimum.accumulate(z-.102*ds)+.102*ds
        z=np.minimum.accumulate((z+.102*ds)[::-1])[::-1]-.102*ds
        if len(z)>1:grade=float(np.max(np.abs(np.diff(z))/np.diff(ds)))
        else:grade=0
        edge_export.append({k:v for k,v in e.items() if k!='line'}|{'points':np.c_[p,z].round(5).tolist(),'length':float(ds[-1]),'max_grade':grade})
        sample_xy.extend(p.tolist());sample_h.extend(z.tolist());sample_w.extend([e['width']]*len(p));sample_bridge.extend([e['bridge']]*len(p))
    for ni,n in enumerate(nodes):n['z']=float(h[ni])
    junctions=[]
    for ni,n in enumerate(nodes):
        if not n['edges']:continue
        full=[];asphalt=[];p=np.array(n['xy']);radius=n['radius']
        for ei in n['edges']:
            edge=edge_export[ei];pp=np.array(edge['points'])[:,:2]
            if edge['b']==ni:pp=pp[::-1]
            line=LineString(pp);stop=min(radius,line.length*.49);q=line.interpolate(stop)
            arm=LineString([p,q.coords[0]])
            full.append(arm.buffer(edge['width']/2,cap_style=2,join_style=2))
            asphalt.append(arm.buffer(edge['width']/2-1.49,cap_style=2,join_style=2))
        full=unary_union(full).convex_hull.buffer(.85,join_style=2);asphalt=unary_union(asphalt).convex_hull.buffer(.85,join_style=2)
        patches=[]
        for mat,poly in [('asphalt',asphalt),('sidewalk',full.difference(asphalt))]:
            for tri in triangulate(poly):
                if poly.covers(tri.representative_point()):patches.append({'material':mat,'xy':list(tri.exterior.coords)[:3]})
        reg=edge_export[n['edges'][0]]['region']
        junctions.append({'node':ni,'region':reg,'z':n['z'],'patches':patches})
    sample_xy=np.array(sample_xy);sample_h=np.array(sample_h);sample_w=np.array(sample_w);sample_bridge=np.array(sample_bridge)
    seg_a=[];seg_b=[];seg_za=[];seg_zb=[];seg_width=[];corridor=[]
    for edge in edge_export:
        p=np.array(edge['points']);seg_a.extend(p[:-1,:2]);seg_b.extend(p[1:,:2]);seg_za.extend(p[:-1,2]);seg_zb.extend(p[1:,2]);seg_width.extend([edge['width']]*max(len(p)-1,0))
        tangent=np.gradient(p[:,:2],axis=0);tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-9);normal=np.c_[-tangent[:,1],tangent[:,0]]
        for factor in [-.5,-.24,0,.24,.5]:corridor.extend(p[:,:2]+normal*(edge['width']*factor))
        for sign in [-1,1]:corridor.extend(p[:,:2]+normal*sign*(edge['width']/2+3))
    seg_a=np.array(seg_a);seg_b=np.array(seg_b);seg_delta=seg_b-seg_a;seg_za=np.array(seg_za);seg_zb=np.array(seg_zb);seg_width=np.array(seg_width);seg_tree=cKDTree((seg_a+seg_b)/2);corridor=np.array(corridor)
    def road_projection(x,y):
        co=np.c_[np.asarray(x).ravel(),np.asarray(y).ravel()];_,ii=seg_tree.query(co,k=6)
        delta=seg_delta[ii];tt=np.clip(np.sum((co[:,None,:]-seg_a[ii])*delta,axis=-1)/np.maximum(np.sum(delta*delta,axis=-1),1e-8),0,1)
        proj=seg_a[ii]+delta*tt[:,:,None];dd=np.linalg.norm(co[:,None,:]-proj,axis=-1);choice=np.argmin(dd,axis=1);row=np.arange(len(co));jj=ii[row,choice];t=tt[row,choice]
        return dd[row,choice],seg_width[jj]/2,seg_za[jj]+(seg_zb[jj]-seg_za[jj])*t
    def engineered_height(x,y):
        x=np.asarray(x);y=np.asarray(y);base=raw_height(x,y);co=np.c_[x.ravel(),y.ravel()]
        dis,widths,roadz=road_projection(x,y)
        transition=np.maximum(16,np.abs(base.ravel()-roadz)*3)
        blend=1-smoothstep((dis-widths-3)/transition)
        return (base.ravel()*(1-blend)+(roadz-.10)*blend).reshape(x.shape)
    for junction in junctions:
        incident=[edge_export[i] for i in nodes[junction['node']]['edges']]
        local_a=[];local_b=[];local_za=[];local_zb=[]
        for edge in incident:
            pp=np.array(edge['points']);local_a.extend(pp[:-1,:2]);local_b.extend(pp[1:,:2]);local_za.extend(pp[:-1,2]);local_zb.extend(pp[1:,2])
        local_a=np.array(local_a);local_b=np.array(local_b);local_za=np.array(local_za);local_zb=np.array(local_zb);local_d=local_b-local_a
        for patch in junction['patches']:
            points=np.array(patch['xy']);tt=np.clip(np.sum((points[:,None,:]-local_a)*local_d,axis=-1)/np.maximum(np.sum(local_d*local_d,axis=-1),1e-8),0,1);proj=local_a+local_d*tt[:,:,None];choice=np.argmin(np.linalg.norm(points[:,None,:]-proj,axis=-1),axis=1);elevations=local_za[choice]+(local_zb[choice]-local_za[choice])*tt[np.arange(len(points)),choice];patch['z']=elevations.tolist()
    # Connected components are measured on centreline topology, including bridges.
    seen=set();components=[]
    for ni in range(len(nodes)):
        if ni in seen:continue
        todo=[ni];part=[]
        while todo:
            x=todo.pop()
            if x in seen:continue
            seen.add(x);part.append(x)
            for ei in nodes[x]['edges']:
                e=edges[ei];todo.append(e['b'] if e['a']==x else e['a'])
        components.append(part)
    # Give intentional dead-end/viewpoint spurs and clipped grid termini access.
    if len(components)>1:
        detail=[[(edges[ei]['name'],nodes[ni]['xy']) for ni in c for ei in nodes[ni]['edges'][:1]] for c in components if len(c)<10]
        raise RuntimeError('Road network has disconnected components: '+str([len(c) for c in components])+' '+str(detail))
    # Build footprints are all boxes. Height and density vary by district only.
    exclusion=unary_union([r['line'].buffer(r['width']/2+8) for r in ROUTES])
    buildings=[];reserved=[]
    def district(u,v,reg):
        if reg=='MAIN':
            if v<157:return None
            if 345<u<603 and 168<v<316:return 'CBD'
            if u>603 and v<315:return 'CIVIC'
            if u<345 and v<257:return 'UNIVERSITY'
            if v>333 and u<600:return 'OLDTOWN'
            if u>628 and v>325:return 'CULTURE'
            return 'RESIDENTIAL'
        if reg=='WEST':return 'VILLAGE' if v>622 else ('RESORT' if u>265 else None)
        return 'INDUSTRIAL' if u>597 and v<742 else 'FRINGE'
    for reg,poly in ISLANDS.items():
        minx,miny,maxx,maxy=poly.bounds;spacing=57 if reg=='MAIN' else 71
        for x in np.arange(minx+38,maxx-30,spacing):
            for y in np.arange(miny+38,maxy-30,spacing):
                x0=x+RNG.uniform(-8,8);y0=y+RNG.uniform(-8,8);u,v=px((x0,y0));zone=district(u,v,reg)
                if zone is None:continue
                if zone in ['VILLAGE','RESORT','FRINGE'] and RNG.random()<.25:continue
                if zone=='INDUSTRIAL':sx=RNG.uniform(35,52);sy=RNG.uniform(35,51);ht=RNG.uniform(10,25)
                elif zone=='CBD':sx=RNG.uniform(24,39);sy=RNG.uniform(24,40);ht=RNG.uniform(45,147)
                elif zone=='OLDTOWN':sx=RNG.uniform(19,33);sy=RNG.uniform(21,35);ht=RNG.uniform(10,28)
                elif zone=='CIVIC':sx=RNG.uniform(27,41);sy=RNG.uniform(27,39);ht=RNG.uniform(22,75)
                elif zone=='CULTURE':sx=RNG.uniform(27,44);sy=RNG.uniform(28,44);ht=RNG.uniform(13,40)
                else:sx=RNG.uniform(23,39);sy=RNG.uniform(23,40);ht=RNG.uniform(9,39)
                footprint=box(x0-sx/2,y0-sy/2,x0+sx/2,y0+sy/2)
                if not poly.buffer(-26).contains(footprint) or footprint.intersects(exclusion) or footprint.intersects(lake.buffer(35)):continue
                cc=np.array(footprint.exterior.coords);zh=engineered_height(cc[:,0],cc[:,1])
                if np.ptp(zh)>7:continue
                if zone=='CBD' and 450<u<497 and 192<v<235:continue
                buildings.append(dict(name=f'{reg}_{zone}_{len(buildings):04}',region=reg,zone=zone,center=[x0,y0],size=[sx,sy,ht],base=float(np.max(zh)),footprint=list(footprint.exterior.coords)))
    # The landmark remains one deliberately tall placeholder box.
    tx,ty=xy((493,204));sz=[40,40,285]
    fp=box(tx-20,ty-20,tx+20,ty+20)
    if fp.intersects(exclusion):
        tx,ty=xy((493,199));fp=box(tx-20,ty-20,tx+20,ty+20)
    buildings=[b for b in buildings if not box(b['center'][0]-b['size'][0]/2,b['center'][1]-b['size'][1]/2,b['center'][0]+b['size'][0]/2,b['center'][1]+b['size'][1]/2).intersects(fp.buffer(12))]
    buildings.append(dict(name='MAIN_CBD_Tianming_Tower_PLACEHOLDER',region='MAIN',zone='LANDMARK',center=[tx,ty],size=sz,base=float(engineered_height(np.array([tx]),np.array([ty]))[0]),footprint=list(fp.exterior.coords)))
    # Low box-only docks, cargo stacks and warehouse massing.
    props=[]
    for p,s in [((696,513),(36,100,5)),((720,528),(32,92,5)),((750,553),(29,83,5))]:
        xx,yy=xy(p);props.append(dict(name=f'Port_Pier_{len(props)}',center=[xx,yy],size=list(s),base=1.5,zone='DOCK'))
    # Roads replace the terrain inside their actual footprint. Clipping triangles
    # exactly at that footprint prevents grass from cutting through the pavement
    # at a hill bend or a junction; shoulders remain attached to the road bed.
    road_cutters=[LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2-.02,cap_style=2,join_style=2) for e in edge_export]
    for junction in junctions:
        road_cutters.append(unary_union([Polygon(p['xy']) for p in junction['patches']]).buffer(-.02))
    road_cutters=np.array([p for p in road_cutters if not p.is_empty],dtype=object)
    cutters_tree=shapely.STRtree(road_cutters)
    # Terrain uses a shore-conforming triangulation, with road cuts and lot pads.
    for reg,poly0 in ISLANDS.items():
        poly=poly0.difference(lake) if reg=='WEST' else poly0
        minx,miny,maxx,maxy=poly.bounds;xx,yy=np.meshgrid(np.arange(minx,maxx,12),np.arange(miny,maxy,12));mask=contains_xy(poly,xx.ravel(),yy.ravel());pts=np.c_[xx.ravel()[mask],yy.ravel()[mask]]
        boundaries=[np.array(poly.exterior.coords)]+[np.array(r.coords) for r in poly.interiors]
        road_points=corridor[contains_xy(poly,corridor[:,0],corridor[:,1])]
        pts=np.vstack([pts,road_points]+boundaries);pts=np.unique(np.round(pts,4),axis=0)
        tri=Delaunay(pts);centers=pts[tri.simplices].mean(axis=1);simp=tri.simplices[contains_xy(poly,centers[:,0],centers[:,1])]
        z=engineered_height(pts[:,0],pts[:,1]);coastal=shapely.distance(shapely.points(pts[:,0],pts[:,1]),poly0.boundary)
        # Coastline perimeter is a real intertidal slope, not a floating flat cutout.
        z=2.3+(z-2.3)*smoothstep(coastal/25)
        for b in buildings:
            if b['region']!=reg:continue
            cx,cy=b['center'];sx,sy,_=b['size'];d=np.maximum(np.abs(pts[:,0]-cx)-sx/2,np.abs(pts[:,1]-cy)-sy/2);w=1-smoothstep(np.maximum(d,0)/5);z=z*(1-w)+(b['base']-.12)*w
        distance,width,roadz=road_projection(pts[:,0],pts[:,1]);on_road=distance<width+2;z[on_road]=np.minimum(z[on_road],roadz[on_road]-.10)
        polygons=shapely.polygons(pts[simp]);pairs=cutters_tree.query(polygons,predicate='intersects');affected=np.unique(pairs[0])
        for ci in np.unique(pairs[1]):
            ids=pairs[0][pairs[1]==ci];polygons[ids]=shapely.difference(polygons[ids],road_cutters[ci])
        unchanged=np.ones(len(simp),dtype=bool);unchanged[affected]=False
        retained=simp[unchanged].tolist();lookup={tuple(p):i for i,p in enumerate(pts)};extra=[]
        clipped=shapely.get_parts(shapely.constrained_delaunay_triangles(polygons[affected]));clipped=clipped[~shapely.is_empty(clipped)]
        for triangle in clipped:
            indices=[]
            for p in np.asarray(triangle.exterior.coords)[:3]:
                key=tuple(np.round(p,4))
                if key not in lookup:lookup[key]=len(pts)+len(extra);extra.append(key)
                indices.append(lookup[key])
            retained.append(indices)
        if extra:
            extra=np.array(extra);ez=engineered_height(extra[:,0],extra[:,1]);pts=np.vstack([pts,extra]);z=np.r_[z,ez]
        simp=np.array(retained,dtype=np.int32)
        np.savez_compressed(out/f'terrain_{reg}.npz',vertices=np.c_[pts,z].astype(np.float32),faces=simp.astype(np.int32),coast=np.array(poly0.exterior.coords,dtype=np.float32))
    stats={'map_size_m':[4000,4000],'road_length_m':sum(e['length'] for e in edge_export),'routes':len({r['name'] for r in ROUTES}),'road_edges':len(edges),'junctions':sum(len(n['edges'])>=3 for n in nodes),'buildings':len(buildings),'connected_components':len(components),'maximum_road_grade':max(e['max_grade'] for e in edge_export),'road_surface_height_range_m':[float(sample_h.min()),float(sample_h.max())]}
    data={'schema':'hero13.city.blockout.v1','scale':1,'axes':'Blender Z up; GLB Y up; north +Y Blender / -Z GLB','coasts':{k:list(v.exterior.coords) for k,v in ISLANDS.items()},'lake':list(lake.exterior.coords),'lake_level':22,'nodes':nodes,'junctions':junctions,'edges':edge_export,'buildings':buildings,'props':props,'stats':stats,'sources':{'road':{'title':'Road Modular','author':'mortalityrexotable','license':'CC-BY-4.0','url':'https://sketchfab.com/3d-models/road-modular-74f74f8569ac410f80266d3f1603bffd'},'layout':'User supplied three-island city concept map'}}
    (out/'city_plan.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print(json.dumps(stats,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'generated');args=ap.parse_args();main(args.out)
