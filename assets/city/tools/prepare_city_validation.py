"""Independent topology audit and distributed sidewalk ray targets for Blender."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from scipy.spatial import cKDTree
try:import shapely
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'runtime/py'));import shapely
from shapely.geometry import LineString,box
from create_city_plan import LAND

ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--templates',type=Path,required=True);args=ap.parse_args()
base=args.plan;plan=json.loads((base/'city_plan.json').read_text())
fp=json.loads((base/'surface_footprints.json').read_text())
pavement=shapely.from_geojson(fp['pavement']);walks=shapely.from_geojson(fp['sidewalks']);full=shapely.from_geojson(fp['full'])
nodes=plan['nodes'];edges=plan['edges'];adj=[[] for _ in nodes]
for i,e in enumerate(edges):
    assert e['a']!=e['b'] and e['length']>.01
    adj[e['a']].append(e['b']);adj[e['b']].append(e['a'])
    assert i in nodes[e['a']]['edges'] and i in nodes[e['b']]['edges']
seen=set();components=[]
for i in range(len(nodes)):
    if i in seen:continue
    todo=[i];part=[]
    while todo:
        k=todo.pop()
        if k in seen:continue
        seen.add(k);part.append(k);todo.extend(adj[k])
    components.append(part)
assert len(components)==1
assert pavement.is_valid and walks.is_valid and full.is_valid
pavement_parts=len([p for p in shapely.get_parts(pavement) if p.area>.01]);assert pavement_parts==1
asphalt_walk_overlap=walks.intersection(pavement).area;assert asphalt_walk_overlap<.001
encroach=[]
for b in plan['buildings']:
    x,y=b['center'];sx,sy,_=b['size'];p=box(x-sx/2,y-sy/2,x+sx/2,y+sy/2)
    if full.intersects(p):encroach.append(b['name'])
assert not encroach
sa=[];sb=[];za=[];zb=[];carriage_half=[];maxgrade=0;sharp=0;endpoint_error=0
for e in edges:
    q=np.array(e['points']);ds=np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1)
    maxgrade=max(maxgrade,float(np.max(np.abs(np.diff(q[:,2]))/ds)))
    endpoint_error=max(endpoint_error,abs(q[0,2]-nodes[e['a']]['z']),abs(q[-1,2]-nodes[e['b']]['z']))
    tangent=np.diff(q[:,:2],axis=0);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
    angle=np.degrees(np.arccos(np.clip(np.sum(tangent[1:]*tangent[:-1],axis=1),-1,1)))
    if len(angle) and max(angle)>25:sharp+=1
    sa.extend(q[:-1,:2]);sb.extend(q[1:,:2]);za.extend(q[:-1,2]);zb.extend(q[1:,2])
    carriage_half.extend([e['carriage_width']/2]*(len(q)-1))
assert maxgrade<=.085001 and endpoint_error<.0001
near_pairs=cKDTree(np.array([n['xy'] for n in nodes])).query_pairs(.75)
near_height_error=max((abs(nodes[a]['z']-nodes[b]['z']) for a,b in near_pairs),default=0)
assert near_height_error<.001,'Nearly coincident junctions carry different elevations'
sa=np.array(sa);sb=np.array(sb);delta=sb-sa;za=np.array(za);zb=np.array(zb);carriage_half=np.array(carriage_half);tree=cKDTree((sa+sb)/2)
xx,yy=np.meshgrid(np.arange(-1998,2000,4),np.arange(-1997,2000,4));samples=np.c_[xx.ravel(),yy.ravel()]
shapely.prepare(walks)
# Avoid points within 2 mm of the outer footprint boundary: at kilometre-scale
# coordinates, float32 GLB positions have a sub-millimetre quantization step.
test_interior=walks.buffer(-.002)
samples=samples[shapely.contains_xy(test_interior,samples[:,0],samples[:,1])]
_,ii=tree.query(samples,k=12);d=delta[ii]
t=np.clip(np.sum((samples[:,None]-sa[ii])*d,axis=-1)/np.maximum(np.sum(d*d,axis=-1),1e-10),0,1)
proj=sa[ii]+d*t[:,:,None];choice=np.argmin(np.linalg.norm(samples[:,None]-proj,axis=-1),axis=1);row=np.arange(len(samples));ids=ii[row,choice]
z=za[ids]+(zb[ids]-za[ids])*t[row,choice]
np.savez_compressed(base/'sidewalk_validation_samples.npz',samples=np.c_[samples,z].astype(np.float64))
def heights(co):
    co=np.asarray(co);_,ii=tree.query(co,k=12);d=delta[ii]
    tt=np.clip(np.sum((co[:,None]-sa[ii])*d,axis=-1)/np.maximum(np.sum(d*d,axis=-1),1e-10),0,1)
    pp=sa[ii]+d*tt[:,:,None];cc=np.argmin(np.linalg.norm(co[:,None]-pp,axis=-1),axis=1);rr=np.arange(len(co));jj=ii[rr,cc]
    return za[jj]+(zb[jj]-za[jj])*tt[rr,cc]
# A continuous, 4 mm recessed top closes sub-millimetre cracks between clipped
# source tiles. Junction fill uses the original Sidewalk 2 top UV transform and
# original slab height; the detailed copied source tiles remain above it.
source=json.loads(args.templates.read_text())['sidewalk'];sv=np.array(source['vertices']);mi=sv.min(0);ma=sv.max(0)
top=next(t for t in source['triangles'] if sv[t['v'],2].min()>ma[2]-.0001)
tv=sv[top['v']];local=np.c_[(tv[:,0]-mi[0])/(ma[0]-mi[0]),(tv[:,1]-mi[1])/(ma[1]-mi[1]),np.ones(3)]
uv_transform=np.linalg.solve(local,np.array(top['uv']))
wtri=[np.array(t.exterior.coords)[:3] for t in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(walks,3))) if not t.is_empty]
co=np.array(wtri);a=co[:,1]-co[:,0];b=co[:,2]-co[:,0];negative=a[:,0]*b[:,1]-a[:,1]*b[:,0]<0;co[negative]=co[negative][:,::-1,:]
flat=co.reshape(-1,2);_,ii=tree.query(flat,k=12);d=delta[ii]
tt=np.clip(np.sum((flat[:,None]-sa[ii])*d,axis=-1)/np.maximum(np.sum(d*d,axis=-1),1e-10),0,1)
proj=sa[ii]+d*tt[:,:,None];choice=np.argmin(np.linalg.norm(flat[:,None]-proj,axis=-1),axis=1);row=np.arange(len(flat));jj=ii[row,choice];proj=proj[row,choice]
hz=za[jj]+(zb[jj]-za[jj])*tt[row,choice]
dir=delta[jj]/np.linalg.norm(delta[jj],axis=1,keepdims=True)
across=np.clip((np.linalg.norm(flat-proj,axis=1)-carriage_half[jj])/3,0,1)
along=np.mod(np.sum(proj*dir,axis=1),ma[1]-mi[1])/(ma[1]-mi[1])
uv=np.c_[across,along,np.ones(len(flat))]@uv_transform
np.savez_compressed(base/'sidewalk_underlay.npz',vertices=np.c_[flat,hz+ma[2]-.0431656-.004].astype(np.float32),faces=np.arange(len(flat),dtype=np.int32).reshape(-1,3),uv=uv.astype(np.float32))
# One continuous slab includes the waterborne T junction between the southern
# bridge and west-east link. Separate straight deck boxes left it unsupported.
deck=full.difference(LAND.buffer(-2));deck=shapely.segmentize(deck,8)
vertices=[];faces=[]
for t in shapely.get_parts(shapely.constrained_delaunay_triangles(deck)):
    if t.is_empty:continue
    co=np.array(t.exterior.coords)[:3];hz=heights(co)
    cross=(co[1,0]-co[0,0])*(co[2,1]-co[0,1])-(co[1,1]-co[0,1])*(co[2,0]-co[0,0])
    if cross<0:co=co[::-1];hz=hz[::-1]
    off=len(vertices);vertices.extend(np.c_[co,hz-.10].tolist());vertices.extend(np.c_[co,hz-1.5].tolist());faces.extend([[off,off+1,off+2],[off+5,off+4,off+3]])
for p in shapely.get_parts(deck):
    if p.geom_type!='Polygon':continue
    for r in [p.exterior]+list(p.interiors):
        co=np.array(r.coords);hz=heights(co)
        for i in range(len(co)-1):
            off=len(vertices);vertices.extend([[*co[i],hz[i]-.1],[*co[i+1],hz[i+1]-.1],[*co[i+1],hz[i+1]-1.5],[*co[i],hz[i]-1.5]])
            faces.extend([[off,off+1,off+2],[off,off+2,off+3]])
np.savez_compressed(base/'bridge_foundation.npz',vertices=np.array(vertices,np.float32),faces=np.array(faces,np.int32),uv=np.zeros((len(vertices),2),np.float32))
report={'connected_components_measured':len(components),'pavement_polygon_components_measured':pavement_parts,'asphalt_sidewalk_overlap_m2':asphalt_walk_overlap,'sidewalk_width_m':3,'sidewalk_validation_targets':len(samples),'sidewalk_sample_boundary_margin_m':.002,'maximum_grade_measured':maxgrade,'maximum_endpoint_error_m':endpoint_error,'nearcoincident_junction_height_error_m':near_height_error,'sharp_sample_bend_edges_over_25deg':sharp,'placeholder_road_overlap_count':len(encroach),'source_sidewalk_object':plan['stats']['source_sidewalk_object']}
(base/'topology_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
