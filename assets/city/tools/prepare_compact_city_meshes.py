"""Original road kit geometry/UVs on fresh roads, continuous sidewalks and terrain cuts."""
import argparse,json,math
from pathlib import Path
from compact_city_math import *
from optimize_city_plan import asset_triangles,clip_poly_y
from shapely.geometry import box
from scipy.spatial import Delaunay

class Buffer:
    def __init__(self):self.v=[];self.uv=[]
    def add(self,v,uv=None):
        q=np.asarray(v,float).reshape(-1,3,3);u=np.asarray(uv,float).reshape(-1,3,2) if uv is not None else np.tile([.7,.82],(len(q),3,1))
        flip=(q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0])<0
        q[flip]=q[flip,::-1];u[flip]=u[flip,::-1];self.v.append(q.reshape(-1,3));self.uv.append(u.reshape(-1,2))
    def save(self,path):
        v=np.concatenate(self.v).astype(np.float32) if self.v else np.empty((0,3),np.float32);uv=np.concatenate(self.uv).astype(np.float32) if self.uv else np.empty((0,2),np.float32)
        np.savez_compressed(path,vertices=v,uv=uv,faces=np.arange(len(v),dtype=np.int32).reshape(-1,3));return len(v)//3

def rings(poly):
    for p in shapely.get_parts(poly):
        if p.geom_type!='Polygon':continue
        yield np.asarray(p.exterior.coords)
        for r in p.interiors:yield np.asarray(r.coords)

def triangles(poly,step=4):
    out=shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(poly,max_segment_length=step)));out=out[~shapely.is_empty(out)]
    return np.asarray([np.asarray(t.exterior.coords)[:3] for t in out]) if len(out) else np.empty((0,3,2))

def bounded_triangles(poly,grid=12):
    # Bound pavement triangle spans, so curved vertical profiles are sampled locally
    # and planar BVH queries stay stable after GLB float32 quantization.
    if poly.is_empty:return np.empty((0,3,2))
    x0,y0,x1,y1=poly.bounds;xx,yy=np.meshgrid(np.arange(math.floor(x0/grid)*grid,x1,grid),np.arange(math.floor(y0/grid)*grid,y1,grid));cells=shapely.box(xx.ravel(),yy.ravel(),xx.ravel()+grid,yy.ravel()+grid);cells=cells[shapely.intersects(poly,cells)];return triangles(shapely.intersection(cells,poly),4)

def main(a):
    p=json.loads(a.plan.read_text());edges=p['edges'];islands={k:Polygon(v) for k,v in p['coasts'].items()};lake=Polygon(p['lake']);land=unary_union(list(islands.values())).difference(lake)
    a.out.mkdir(parents=True,exist_ok=True);templates=json.loads(a.templates.read_text());prep={k:asset_triangles(templates[k],k) for k in ['local','arterial','sidewalk']};groups=[];footprints={};report={}
    ground=[e for e in edges if e['layer'].startswith('GROUND')]
    for e in edges:
        if e['layer'].endswith('UPPER'):
            co=np.array(e['points']);diff=co[:,2]-raw_height(co[:,:2],islands,lake)
            if abs(diff).max()<2.:ground.append(e)
    gp=SurfaceProjector(ground)
    def terrain(xy):return terrain_height(xy,islands,lake,gp)
    for layer in sorted({e['layer'] for e in edges}):
        ee=[e for e in edges if e['layer']==layer];pp=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,quad_segs=4) for e in ee]);ff=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,quad_segs=4) for e in ee]);footprints[layer]={'road':pp,'full':ff}
    if not a.terrain_only:
        for gi,(layer,fp) in enumerate(footprints.items()):
            ee=[e for e in edges if e['layer']==layer];proj=SurfaceProjector(ee);P=fp['road'];F=fp['full'];connected=[];owned_road_cuts=[];owned_walk_cuts=[];neighbor_ids=set()
            def priority(name):return (0 if name.startswith('GROUND') else 1 if name.endswith('UPPER') else 3 if name=='WATER_BRIDGES' else 2,name)
            for e in ee:
                for ni in [e['a'],e['b']]:
                    for ei in p['nodes'][ni]['edges']:
                        o=edges[ei]
                        if o['layer']==layer or ei in neighbor_ids:continue
                        neighbor_ids.add(ei);line=LineString(np.array(o['points'])[:,:2]);part=line.buffer(o['carriage_width']/2,quad_segs=4);connected.append(part)
                        if priority(o['layer'])<priority(layer):owned_road_cuts.append(part);owned_walk_cuts.append(line.buffer(o['width']/2,quad_segs=4))
            if connected:Pmask=unary_union([P,*connected])
            else:Pmask=P
            W=F.difference(Pmask)
            if owned_road_cuts:P=P.difference(unary_union(owned_road_cuts))
            if owned_walk_cuts:W=W.difference(unary_union(owned_walk_cuts))
            road=Buffer();walk=Buffer();base=Buffer();curb=Buffer();shapely.prepare(P)
            def surface(poly,buffer,off,uvwalk=False):
                t=bounded_triangles(poly,12)
                if not len(t):return
                co=t.reshape(-1,2);z=proj.height(co)+off
                if uvwalk:
                    d,w,_,ii,tt=proj.project(co);along=np.linalg.norm(proj.a[ii,:2]+proj.d[ii,:2]*tt[:,None],axis=1);uv=np.c_[.271-.055*np.clip((d-(w-2))/2,0,1),.7766-.1777*np.mod(along,16.9048)/16.9048]
                else:uv=np.tile([.70,.82],(len(co),1))
                buffer.add(np.c_[co,z].reshape(-1,3,3),uv.reshape(-1,3,2))
            surface(P,base,-.008);surface(W,walk,.139577,True)
            for ei,e in enumerate(ee):
                start,stop=e['range'];typ='arterial' if e['carriage_width']>=15 else 'local';tris,period,half=prep[typ]
                def tiled(tris,period):
                    out=[]
                    for tile in np.arange(start,stop-.01,period):
                        available=min(period,stop-tile)
                        for tri in tris:
                            part=tri.copy() if available>=period-.001 else clip_poly_y(tri,available,False)
                            for k in range(1,len(part)-1):
                                q=part[[0,k,k+1]].copy();q[:,1]+=tile;out.append(q)
                    return np.asarray(out)
                q=tiled(tris,period)
                if len(q):
                    flat=q.reshape(-1,5);co,n=frame(e,flat[:,1]);co[:,:2]+=n*(flat[:,0]*e['carriage_width']/(2*half))[:,None];zz=flat[:,2].copy();median=np.abs(flat[:,0])<2;zz[median]*=smoothstep(np.minimum(flat[median,1]-start,stop-flat[median,1])/18);co[:,2]+=zz;xyz=co.reshape(-1,3,3);poly=shapely.polygons(xyz[:,:,:2]);inside=shapely.covers(P,poly);det=(xyz[:,1,0]-xyz[:,0,0])*(xyz[:,2,1]-xyz[:,0,1])-(xyz[:,1,1]-xyz[:,0,1])*(xyz[:,2,0]-xyz[:,0,0]);vertical=np.abs(det)<1e-8;inside|=vertical&shapely.intersects_xy(P,xyz[:,:,0].mean(1),xyz[:,:,1].mean(1))
                    if np.any(inside):road.add(xyz[inside],q[inside,:,3:])
                    for ti in np.flatnonzero((~inside)&(~vertical)&shapely.intersects(P,poly)):
                        ts=triangles(poly[ti].intersection(P),100)
                        if not len(ts):continue
                        xy=ts.reshape(-1,2);aa,bb,cc=xyz[ti,:,:2];u=bb-aa;v=cc-aa;d=xy-aa;dd=u[0]*v[1]-u[1]*v[0];s=(d[:,0]*v[1]-d[:,1]*v[0])/dd;t=(u[0]*d[:,1]-u[1]*d[:,0])/dd;weight=np.c_[1-s-t,s,t];road.add(np.c_[xy,weight@xyz[ti,:,2]].reshape(-1,3,3),(weight@q[ti,:,3:]).reshape(-1,3,2))
                wt,wp,_=prep['sidewalk'];q=tiled(wt,wp)
                if not len(q):continue
                flat=q.reshape(-1,5);co,n=frame(e,flat[:,1])
                for side in [-1,1]:
                    pos=co.copy();pos[:,:2]+=n*(side*(e['carriage_width']/2+flat[:,0]*e['sidewalk_width']))[:,None];pos[:,2]+=flat[:,2]
                    for xyz,source in zip(pos.reshape(-1,3,3),q):
                        poly=Polygon(xyz[:,:2])
                        if poly.area<1e-8:continue
                        clip=poly if W.covers(poly) else poly.intersection(W)
                        if clip.is_empty:continue
                        if clip.equals(poly):walk.add(xyz[None],source[None,:,3:]);continue
                        ts=triangles(clip,100)
                        if not len(ts):continue
                        xy=ts.reshape(-1,2);a0,b,c=xyz[:,:2];u=b-a0;v=c-a0;det=u[0]*v[1]-u[1]*v[0]
                        if abs(det)<1e-10:continue
                        d=xy-a0;s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det;weights=np.c_[1-s-t,s,t];walk.add(np.c_[xy,weights@xyz[:,2]].reshape(-1,3,3),(weights@source[:,3:]).reshape(-1,3,2))
            # Source-atlas curb skirts follow complete walk boundaries, with open road mouths.
            for ring in rings(shapely.segmentize(W,max_segment_length=4)):
                zz=proj.height(ring)
                for a0,b,za,zb in zip(ring[:-1],ring[1:],zz[:-1],zz[1:]):
                    v=np.array([[*a0,za+.143577],[*b,zb+.143577],[*b,zb-.10],[*a0,za-.10]]);curb.v.append(v[[0,1,2,0,2,3]]);curb.uv.append(np.tile([.216,.67],(6,1)))
            for kind,buf in [('road_kit',road),('pavement',base),('sidewalk',walk),('curb',curb)]:
                name=f'{layer}_{kind}.npz';nt=buf.save(a.out/name);groups.append({'layer':layer,'kind':kind,'file':name,'triangles':nt})
            print('SURFACE_GROUP_COMPLETE',layer,flush=True)
        (a.out/'surface_groups.json').write_text(json.dumps(groups,indent=2));(a.out/'surface_footprints.json').write_text(json.dumps({k:{q:shapely.to_geojson(v) for q,v in r.items()} for k,r in footprints.items()},separators=(',',':')))
    cutter=unary_union([footprints[k]['full'] for k in footprints if k.startswith('GROUND')])
    # Cut at-grade approach surfaces; leave ground below the elevated sections intact.
    atgrade=[]
    for e in edges:
        if not e['layer'].startswith('IX'):continue
        co=np.array(e['points']);dz=co[:,2]-terrain(co[:,:2])
        for i in range(len(co)-1):
            if max(dz[i],dz[i+1])<1.4:atgrade.append(LineString(co[i:i+2,:2]).buffer(e['width']/2,quad_segs=3))
    sourcepads=[Polygon(r['pad_xy']) for r in p['real_buildings']]+[Polygon(r['plaza_xy']) for r in p['real_buildings'] if 'plaza_xy' in r];alleycuts=[LineString(r['points']).buffer(r['width']/2+.03,cap_style=2) for r in p['pedestrian_alleys']]
    cutter=unary_union([cutter.buffer(-.025),*atgrade,*sourcepads,*alleycuts]);report['terrain']={}
    for reg,poly in islands.items():
        domain=poly.difference(lake) if reg=='WEST' else poly;domain=domain.difference(cutter);vv=[];ff=[];off=0
        for parcel in shapely.get_parts(domain):
            if parcel.geom_type!='Polygon' or parcel.area<.001:continue
            b=parcel.bounds;xx,yy=np.meshgrid(np.arange(b[0],b[2],14),np.arange(b[1],b[3],14));pts=np.c_[xx.ravel(),yy.ravel()];pts=pts[shapely.contains_xy(parcel,pts[:,0],pts[:,1])];pts=np.unique(np.round(np.vstack([pts,*rings(shapely.segmentize(parcel,max_segment_length=5))]),5),axis=0)
            if len(pts)<3:continue
            tri=Delaunay(pts).simplices;polys=shapely.polygons(pts[tri]);mask=shapely.covers(parcel.buffer(.00002),polys);kept=tri[mask];touched=(~mask)&shapely.intersects(parcel,polys);more=triangles(shapely.intersection(polys[touched],parcel),1000)
            if len(more):
                flat=more.reshape(-1,2);tr=np.arange(len(flat)).reshape(-1,3)+len(pts);pts=np.vstack([pts,flat]);kept=np.vstack([kept,tr])
            z=terrain(pts);vv.append(np.c_[pts,z]);ff.append(kept+off);off+=len(pts)
        co=np.concatenate(vv).astype(np.float32);faces=np.concatenate(ff).astype(np.int32);t=co[faces,:2];det=(t[:,1,0]-t[:,0,0])*(t[:,2,1]-t[:,0,1])-(t[:,1,1]-t[:,0,1])*(t[:,2,0]-t[:,0,0]);faces[det<0]=faces[det<0,::-1];np.savez_compressed(a.out/f'terrain_{reg}.npz',vertices=co,faces=faces);report['terrain'][reg]={'vertices':len(co),'triangles':len(faces)};print('TERRAIN_COMPLETE',reg,len(faces),flush=True)
    (a.out/'mesh_report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--templates',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--terrain-only',action='store_true');main(ap.parse_args())
