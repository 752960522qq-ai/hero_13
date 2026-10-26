"""Repair the first city plan and assemble roads/sidewalks from original kit UVs.

The baseline graph is the layout, not the final mesh. This pass reconnects
nearby street ends, merges tiny intersection fragments, fairs their approaches,
and uses a common polygon footprint for pavement, sidewalks and terrain cuts.
"""
from pathlib import Path
import argparse, collections, gzip, heapq, json, math, sys
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree,Delaunay
from scipy.interpolate import CubicSpline
try:
    import shapely
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'runtime/py'))
    import shapely
from shapely.geometry import Point,LineString,Polygon,MultiPoint,box
from shapely.ops import unary_union,nearest_points,substring
from create_city_plan import raw_height,ISLANDS,LAND,lake,smoothstep

WALK_WIDTH=3.0
ROAD_Z=.0431656
FRAME_CACHE={}

def cross2(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]

def read_json(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())

def components(nodes,edges):
    seen=set();parts=[]
    for i,n in enumerate(nodes):
        if i in seen or not n['edges']:continue
        todo=[i];part=[]
        while todo:
            j=todo.pop()
            if j in seen:continue
            seen.add(j);part.append(j)
            for k in nodes[j]['edges']:
                e=edges[k];todo.append(e['b'] if e['a']==j else e['a'])
        parts.append(part)
    return parts

def fair(points,strength=11):
    """Remove snap-induced hooks, keeping both graph endpoints fixed."""
    p=np.asarray(points,float)[:,:2]
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>.01]]
    if len(p)<2:return p
    ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    s=np.linspace(0,ds[-1],max(3,int(ds[-1]/2)+1))
    q=np.c_[np.interp(s,ds,p[:,0]),np.interp(s,ds,p[:,1])]
    # Filtering extends tangent lines, avoiding the endpoint pinching of a
    # constant-padding filter. The final linear correction preserves nodes.
    pad=24
    step0=q[1]-q[0];step1=q[-1]-q[-2]
    ext=np.vstack([q[0]-np.arange(pad,0,-1)[:,None]*step0,q,
                   q[-1]+np.arange(1,pad+1)[:,None]*step1])
    out=gaussian_filter1d(ext,min(strength/2,max(1,len(q)/8)),axis=0,mode='nearest')[pad:-pad]
    t=s/ds[-1];out+=(p[0]-out[0])[None,:]*(1-t[:,None])+(p[-1]-out[-1])[None,:]*t[:,None]
    out[0]=p[0];out[-1]=p[-1]
    return out

def graph_from_lines(records):
    lines=[r['line'] for r in records]
    # Snap endpoints that differ only by the original sampling tolerance.
    end=MultiPoint([p for l in lines for p in [l.coords[0],l.coords[-1]]])
    lines=[shapely.snap(l,end,.3) for l in lines]
    union=unary_union(lines);nodes=[];edges=[];lookup={}
    tree=shapely.STRtree(lines)
    def node(p):
        key=tuple(np.round(p,4))
        if key not in lookup:lookup[key]=len(nodes);nodes.append({'xy':list(key),'edges':[]})
        return lookup[key]
    for line in shapely.get_parts(union):
        if line.geom_type!='LineString' or line.length<.02:continue
        p=line.interpolate(.5,normalized=True);idx=int(tree.nearest(p));r=records[idx]
        a=node(line.coords[0]);b=node(line.coords[-1])
        if a==b and line.length<20:continue
        e={k:v for k,v in r.items() if k!='line'}|{'a':a,'b':b,'line':line}
        j=len(edges);edges.append(e);nodes[a]['edges'].append(j);nodes[b]['edges'].append(j)
    return nodes,edges

def collapse(nodes,edges,limit=26):
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    # A crossing may have been split into two numerical nodes only centimetres
    # apart, with no explicit short edge between them. Merge by position too;
    # otherwise the graph grade solver can assign two heights to one junction.
    for a,b in cKDTree(np.array([n['xy'] for n in nodes])).query_pairs(.75):
        parent[root(a)]=root(b)
    for e in edges:
        if e['line'].length<limit:parent[root(e['a'])]=root(e['b'])
    groups=collections.defaultdict(list)
    for i in range(len(nodes)):groups[root(i)].append(i)
    newnodes=[];remap={}
    for ids in groups.values():
        ni=len(newnodes);w=np.array([max(1,len(nodes[i]['edges'])) for i in ids])
        xy=np.average([nodes[i]['xy'] for i in ids],axis=0,weights=w)
        newnodes.append({'xy':xy.tolist(),'edges':[]})
        for i in ids:remap[i]=ni
    result=[];dedup={}
    for e in edges:
        a,b=remap[e['a']],remap[e['b']]
        if a==b:continue
        p=np.array(e['line'].coords);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        t=ds/ds[-1]
        # Distribute endpoint moves over a short approach instead of adding a
        # kink in the first 6 m sample.
        p+=(np.array(newnodes[a]['xy'])-p[0])[None,:]*(1-smoothstep(ds/55))[:,None]
        p+=(np.array(newnodes[b]['xy'])-p[-1])[None,:]*(1-smoothstep((ds[-1]-ds)/55))[:,None]
        p[0]=newnodes[a]['xy'];p[-1]=newnodes[b]['xy'];p=fair(p,12)
        line=LineString(p);key=(min(a,b),max(a,b))
        if key in dedup:
            other=result[dedup[key]]
            if line.hausdorff_distance(other['line'])<max(12,e['original_width']*.75):
                if e['original_width']>other['original_width']:other.update({k:v for k,v in e.items() if k not in ['a','b','line']})
                continue
        dedup[key]=len(result);result.append(e|{'a':a,'b':b,'line':line})
    for i,e in enumerate(result):newnodes[e['a']]['edges'].append(i);newnodes[e['b']]['edges'].append(i)
    return newnodes,result

def stitch_ends(nodes,edges):
    """Reconnect clipped grid/ring ends, preferring the continuing direction."""
    changes=0
    for ni,n in enumerate(nodes):
        if len(n['edges'])!=1:continue
        ei=n['edges'][0];edge=edges[ei];p=np.array(edge['line'].coords)
        reverse=edge['a']==ni
        if reverse:p=p[::-1]
        end=p[-1];direction=end-p[max(0,len(p)-12)];direction/=max(np.linalg.norm(direction),1e-9)
        candidates=[]
        for j,e in enumerate(edges):
            if j==ei:continue
            line=e['line'];near=nearest_points(Point(end),line)[1];q=np.array(near.coords[0]);d=np.linalg.norm(q-end)
            if d>145:continue
            delta=(q-end)/max(d,1e-8);cos=float(delta@direction)
            if d>4 and cos<-.25:continue
            connector=LineString([end,q])
            if not LAND.buffer(-5).covers(connector) or connector.intersects(lake.buffer(8)):continue
            score=d+32*(1-cos)
            if e['name']==edge['name']:score-=30
            candidates.append((score,j,q))
        if not candidates:continue
        _,j,q=min(candidates,key=lambda x:x[0])
        target=edges[j];s=target['line'].project(Point(q));L=target['line'].length
        if s<25:q=np.array(nodes[target['a']]['xy'])
        elif L-s<25:q=np.array(nodes[target['b']]['xy'])
        displacement=q-end
        ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        # Blend a long enough section of the original spur into its junction.
        w=1-smoothstep((ds[-1]-ds)/max(65,np.linalg.norm(displacement)*1.4))
        p+=w[:,None]*displacement;p[-1]=q
        p=fair(p,10)
        if reverse:p=p[::-1]
        edge['line']=LineString(p);changes+=1
    return changes

def frame(edge,dist):
    key=id(edge)
    if key not in FRAME_CACHE:
        p=np.array(edge['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
        tangent=np.gradient(p[:,:2],ds,axis=0);tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-9)
        FRAME_CACHE[key]=(p,ds,tangent)
    p,ds,tangent=FRAME_CACHE[key]
    s=np.clip(np.asarray(dist),0,ds[-1]);pos=np.stack([np.interp(s,ds,p[:,i]) for i in range(3)],axis=-1)
    t=np.stack([np.interp(s,ds,tangent[:,i]) for i in range(2)],axis=-1);t/=np.maximum(np.linalg.norm(t,axis=-1,keepdims=True),1e-9)
    return pos,np.stack([-t[...,1],t[...,0]],axis=-1)

class Buffer:
    def __init__(self):self.v=[];self.uv=[]
    def add(self,v,uv):
        self.v.append(np.asarray(v,np.float32).reshape(-1,3));self.uv.append(np.asarray(uv,np.float32).reshape(-1,2))
    def save(self,path):
        v=np.concatenate(self.v) if self.v else np.empty((0,3),np.float32)
        uv=np.concatenate(self.uv) if self.uv else np.empty((0,2),np.float32)
        np.savez_compressed(path,vertices=v,faces=np.arange(len(v),dtype=np.int32).reshape(-1,3),uv=uv)

def clip_poly_y(data,level,above):
    """Sutherland-Hodgman, retaining XYZ and UV interpolation."""
    out=[]
    for a,b in zip(data,np.roll(data,-1,axis=0)):
        ia=(a[1]>=level-1e-8) if above else (a[1]<=level+1e-8)
        ib=(b[1]>=level-1e-8) if above else (b[1]<=level+1e-8)
        if ia:out.append(a)
        if ia!=ib:out.append(a+(b-a)*(level-a[1])/(b[1]-a[1]))
    return np.array(out)

def asset_triangles(template,kind):
    v=np.array(template['vertices']);mi=v.min(0);ma=v.max(0)
    if kind=='sidewalk':
        v[:,0]=(v[:,0]-mi[0])/(ma[0]-mi[0]);v[:,1]-=mi[1]
        v[:,2]-=ROAD_Z;y0,y1=0,ma[1]-mi[1]
    else:
        v[:,0]-=(mi[0]+ma[0])/2;v[:,1]-=mi[1];v[:,2]-=ROAD_Z
        y0,y1=(12,50) if kind=='arterial' else (0,ma[1]-mi[1])
    result=[]
    inner=(ma[0]-mi[0])/2-1.46
    for t in template['triangles']:
        q=v[t['v']];data=np.c_[q,np.array(t['uv'])]
        if kind=='sidewalk':
            if q[:,2].min()<.12:continue  # original top faces; boundary curbs below
        else:
            if q[:,2].max()<-.001:continue # invisible original underside
            if abs(q[:,0].mean())>=inner-.01:continue # replace narrow original walks
            if abs(np.cross(q[1]-q[0],q[2]-q[0])[2])<1e-7 and np.ptp(q[:,1])<.01:continue
        data=clip_poly_y(data,y0,True)
        if len(data)<3:continue
        data=clip_poly_y(data,y1,False)
        if len(data)<3:continue
        for low in np.arange(y0,y1-1e-6,3):
            part=clip_poly_y(data,low,True)
            if len(part)<3:continue
            part=clip_poly_y(part,min(low+3,y1),False)
            if len(part)<3:continue
            for k in range(1,len(part)-1):
                tri=part[[0,k,k+1]].copy();tri[:,1]-=y0
                if np.linalg.norm(np.cross(tri[1,:3]-tri[0,:3],tri[2,:3]-tri[0,:3]))>1e-9:result.append(tri)
    return result,y1-y0,inner

def rings(poly):
    for p in shapely.get_parts(poly):
        if p.geom_type!='Polygon':continue
        yield np.array(p.exterior.coords)
        for r in p.interiors:yield np.array(r.coords)

def dense_polygon(poly,step=3):
    return shapely.segmentize(poly,max_segment_length=step)

def main(args):
    args.out.mkdir(parents=True,exist_ok=True)
    baseline=read_json(args.baseline);assets=read_json(args.templates)
    records=[]
    for e in baseline['edges']:
        records.append({k:e[k] for k in ['name','region','bridge']}|{'original_width':e['width'],'line':LineString(fair(e['points'],13))})
    nodes,edges=graph_from_lines(records);nodes,edges=collapse(nodes,edges,28)
    stitched=stitch_ends(nodes,edges)
    nodes,edges=graph_from_lines(edges);nodes,edges=collapse(nodes,edges,30)
    # A final noding pass preserves crossings introduced by the fairing pass.
    nodes,edges=graph_from_lines(edges)
    nodes,edges=collapse(nodes,edges,14)
    # Collapse can create tiny unused nodes; omit them before exporting.
    used=[i for i,n in enumerate(nodes) if n['edges']];remap={v:i for i,v in enumerate(used)}
    nodes=[nodes[i] for i in used]
    for e in edges:e['a']=remap[e['a']];e['b']=remap[e['b']]
    assert len(components(nodes,edges))==1,'Repair disconnected the road graph'
    for n in nodes:
        n['radius']=max(edges[i]['original_width']/2+8 for i in n['edges'])
    allxy=[n['xy'] for n in nodes];edgeids=[];links=[];flat=[]
    for ei,e in enumerate(edges):
        e['carriage_width']=e['original_width']-3.0;e['sidewalk_width']=WALK_WIDTH;e['width']=e['carriage_width']+2*WALK_WIDTH
        L=e['line'].length;co=np.array([e['line'].interpolate(d).coords[0] for d in np.linspace(0,L,max(3,int(L/4)+1))])
        s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(co,axis=0),axis=1))]
        ra=min(nodes[e['a']]['radius'],L*.42);rb=min(nodes[e['b']]['radius'],L*.42)
        e['range']=[ra,L-rb]
        ids=[e['a']]
        for p in co[1:-1]:ids.append(len(allxy));allxy.append(p.tolist())
        ids.append(e['b']);edgeids.append(ids)
        eff=np.clip(s-ra,0,max(0,L-ra-rb))
        for a,b,d in zip(ids[:-1],ids[1:],np.diff(eff)):links.append((a,b,float(d)))
    allxy=np.array(allxy);height=raw_height(allxy[:,0],allxy[:,1])
    # Preserve raised water crossings, with the grade solver extending the
    # approaches inland as needed; all roads still retain vertical relief.
    for e,ids in zip(edges,edgeids):
        if e['bridge']:
            pp=allxy[ids];water=~shapely.contains_xy(LAND,pp[:,0],pp[:,1]);height[np.array(ids)[water]]=29
    adj=[[] for _ in height]
    for a,b,d in links:adj[a].append((b,.08*d));adj[b].append((a,.08*d))
    heap=[(float(z),i) for i,z in enumerate(height)];heapq.heapify(heap)
    while heap:
        z,i=heapq.heappop(heap)
        if z>height[i]+1e-8:continue
        for j,cost in adj[i]:
            if z+cost<height[j]-1e-8:height[j]=z+cost;heapq.heappush(heap,(float(height[j]),j))
    for n,z in zip(nodes,height):n['z']=float(z)
    for e,ids in zip(edges,edgeids):
        p=allxy[ids];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];z=height[ids].copy()
        # A normalized filter rounds grade breaks without changing flat mouths.
        z=gaussian_filter1d(z,1.6,mode='nearest')
        z[s<=e['range'][0]]=nodes[e['a']]['z'];z[s>=e['range'][1]]=nodes[e['b']]['z']
        z[0]=nodes[e['a']]['z'];z[-1]=nodes[e['b']]['z']
        # Projection after filtering enforces the actual exported sample grade.
        for _ in range(5):
            for k in range(1,len(z)):z[k]=np.clip(z[k],z[k-1]-.085*(s[k]-s[k-1]),z[k-1]+.085*(s[k]-s[k-1]))
            for k in range(len(z)-2,-1,-1):z[k]=np.clip(z[k],z[k+1]-.085*(s[k+1]-s[k]),z[k+1]+.085*(s[k+1]-s[k]))
        assert abs(z[0]-nodes[e['a']]['z'])<1e-5 and abs(z[-1]-nodes[e['b']]['z'])<1e-5
        e['points']=np.c_[p,z].tolist();e['length']=float(s[-1]);e['range'][1]=float(s[-1]-(e['line'].length-e['range'][1]))
        e['max_grade']=float(max(np.abs(np.diff(z))/np.diff(s),default=0))
    # A single shared footprint eliminates the mismatched holes of separately
    # trimmed road/terrain/junction meshes. Sidewalks follow that same boundary.
    baseparts=[e['line'].buffer(e['carriage_width']/2,cap_style=1,join_style=1,quad_segs=5) for e in edges]
    pavement=unary_union(baseparts)
    # Round the reentrant intersection corners, without the old convex-hull
    # aprons that swallowed large triangular islands or formed oversize squares.
    pavement=pavement.buffer(2.2,join_style=1,quad_segs=4).buffer(-2.2,join_style=1,quad_segs=4)
    pavement=shapely.set_precision(pavement,.001)
    walkarea=pavement.buffer(WALK_WIDTH,join_style=1,quad_segs=5).difference(pavement)
    full=pavement.union(walkarea)
    assert len([p for p in shapely.get_parts(pavement) if p.area>.1])==1,'Pavement footprint is not connected'
    print('OPTIMIZED_GRAPH',len(nodes),len(edges),'stitched',stitched,flush=True)
    sa=[];sb=[];za=[];zb=[];sw=[]
    for e in edges:
        p=np.array(e['points']);sa.extend(p[:-1,:2]);sb.extend(p[1:,:2]);za.extend(p[:-1,2]);zb.extend(p[1:,2]);sw.extend([e['width']/2]*(len(p)-1))
    sa=np.array(sa);sb=np.array(sb);sd=sb-sa;za=np.array(za);zb=np.array(zb);sw=np.array(sw);tree=cKDTree((sa+sb)/2)
    def projection(co):
        co=np.asarray(co).reshape(-1,2);_,ii=tree.query(co,k=min(12,len(sa)));delta=sd[ii]
        t=np.clip(np.sum((co[:,None]-sa[ii])*delta,axis=-1)/np.maximum(np.sum(delta*delta,axis=-1),1e-10),0,1)
        proj=sa[ii]+delta*t[:,:,None];dist=np.linalg.norm(co[:,None]-proj,axis=-1);choice=np.argmin(dist,axis=1);row=np.arange(len(co));ids=ii[row,choice];tt=t[row,choice]
        return dist[row,choice],sw[ids],za[ids]+(zb[ids]-za[ids])*tt,ids,tt
    def roadz(co):return projection(co)[2]
    def terrainz(co):
        co=np.asarray(co).reshape(-1,2);base=raw_height(co[:,0],co[:,1]);d,w,z,_,_=projection(co)
        blend=1-smoothstep((d-w-1)/np.maximum(22,np.abs(base-z)*4))
        return base*(1-blend)+(z-.08)*blend
    def surface(poly,out,zoff=0,uvfunc=None):
        triangles=shapely.get_parts(shapely.constrained_delaunay_triangles(dense_polygon(poly,3)))
        triangles=triangles[~shapely.is_empty(triangles)]
        for t in triangles:
            co=np.array(t.exterior.coords)[:3];z=roadz(co)+zoff
            if cross2(co[1]-co[0],co[2]-co[0])<0:co=co[::-1];z=z[::-1]
            uv=uvfunc(co) if uvfunc else np.tile([.70,.82],(3,1))
            out.add(np.c_[co,z],uv)
    if not args.reuse_source_meshes:
        # The road meshes retain original XYZ cross-sections and original UVs.
        # Median-free apron geometry and a continuous base also cover any tiny gaps.
        roadbuf={reg:Buffer() for reg in ['MAIN','WEST','EAST','BRIDGES']}
        walkbuf={reg:Buffer() for reg in ['MAIN','WEST','EAST','BRIDGES']}
        prep={k:asset_triangles(assets[k],k) for k in ['local','arterial','sidewalk','crossing']}
        walkstrips=[];walktriangles=0;roadtriangles=0
        shapely.prepare(walkarea)
        for ei,e in enumerate(edges):
            start,stop=e['range'];L=stop-start
            if L<.05:continue
            if ei%10==0:print('ASSEMBLE_START',ei,round(L,1),flush=True)
            reg=e['region'];typ='arterial' if e['original_width']>=20 else 'local'
            localwalk=walkarea.intersection(e['line'].buffer(e['width']/2+9))
            shapely.prepare(localwalk)
            tris,period,sourcehalf=prep[typ];scale=e['carriage_width']/(sourcehalf*2)
            # Keep the original module at its native longitudinal scale, rather
            # than compressing a 64 m island into every 8 m of road.
            def tiled(triangles,period):
                pieces=[]
                for tile in np.arange(start,stop-.01,period):
                    available=min(period,stop-tile)
                    if available>period-.001:
                        part=np.array(triangles);part[:,:,1]+=tile;pieces.append(part);continue
                    for tri in triangles:
                        part=clip_poly_y(tri,available,False)
                        if len(part)<3:continue
                        for k in range(1,len(part)-1):
                            q=part[[0,k,k+1]].copy();q[:,1]+=tile;pieces.append(q[None,:,:])
                return np.concatenate(pieces)
            q=tiled(tris,period);flat=q.reshape(-1,5);dist=flat[:,1]
            p,n=frame(e,dist);p[:,:2]+=n*(flat[:,0]*scale)[:,None]
            median=np.abs(flat[:,0])<2.0;taper=smoothstep(np.minimum(dist-start,stop-dist)/18)
            zz=flat[:,2].copy();zz[median]*=taper[median];p[:,2]+=zz;p=p.reshape(-1,3,3)
            roadbuf[reg].add(p[:,::-1,:].reshape(-1,3),q[:,::-1,3:].reshape(-1,2));roadtriangles+=len(q)
            # Standalone Sidewalk 2 is copied, narrowed to 3 m, subdivided and bent
            # to the route. Intersections are clipped against the shared road area.
            wtris,wperiod,_=prep['sidewalk']
            edge_walkstrips=[]
            allq=tiled(wtris,wperiod);flat=allq.reshape(-1,5);dist=flat[:,1]
            base,n=frame(e,dist)
            for side in [-1,1]:
                positions=base.copy();positions[:,:2]+=n*(side*(e['carriage_width']/2+flat[:,0]*WALK_WIDTH))[:,None];positions[:,2]+=flat[:,2]
                positions=positions.reshape(-1,3,3)
                for p,q in zip(positions,allq):
                    poly=Polygon(p[:,:2])
                    if poly.area<1e-8:continue
                    clipped=poly if localwalk.covers(poly) else poly.intersection(localwalk)
                    if clipped.is_empty:continue
                    a,b,c=p[:,:2];den=cross2(b-a,c-a)
                    if abs(den)<1e-10:continue
                    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(clipped)):
                        if t.is_empty:continue
                        co=np.array(t.exterior.coords)[:3]
                        w1=cross2(co-a,c-a)/den;w2=cross2(b-a,co-a)/den;weight=np.c_[1-w1-w2,w1,w2]
                        zz=weight@p[:,2];uv=weight@q[:,3:]
                        if cross2(co[1]-co[0],co[2]-co[0])<0:co=co[::-1];zz=zz[::-1];uv=uv[::-1]
                        walkbuf[reg].add(np.c_[co,zz],uv);edge_walkstrips.append(t);walktriangles+=1
            if edge_walkstrips:walkstrips.append(unary_union(edge_walkstrips))
            if ei%100==0:print('ASSEMBLE_EDGE',ei,flush=True)
        original_walk_top=unary_union(walkstrips)
        corners=walkarea.difference(original_walk_top)
        # Corner remesh uses the same source module's affine top UV mapping; it is
        # required for arbitrary-angle junctions instead of stretching rectangular
        # slabs across live traffic lanes.
        def walkuv(co):
            d,w,z,ids,t=projection(co);q=sa[ids]+sd[ids]*t[:,None];cross=np.linalg.norm(co-q,axis=1)
            x=np.clip((cross-(w-WALK_WIDTH))/WALK_WIDTH,0,1)
            # Exact source Sidewalk 2 top UV ranges, derived from its input data.
            vv=np.array(assets['sidewalk']['vertices']);mi=vv.min(0);ma=vv.max(0)
            origin=np.array([.271,.7766]);u=np.array([-.055,0]);v=np.array([0,-.1777])
            along=np.sum(q*sd[ids]/np.maximum(np.linalg.norm(sd[ids],axis=1,keepdims=True),1e-9),axis=1)
            return origin+x[:,None]*u+(np.mod(along,ma[1]-mi[1])/(ma[1]-mi[1]))[:,None]*v
        surface(corners,walkbuf['MAIN'],.143577,walkuv)
        # Curbs follow the complete sidewalk perimeter, leaving every road mouth
        # open. They inherit the original module's slab height and UV colour.
        for ring in rings(dense_polygon(walkarea,3)):
            for a,b in zip(ring[:-1],ring[1:]):
                za0,zb0=roadz(np.array([a,b]));v=np.array([[*a,za0+.143577],[*b,zb0+.143577],[*b,zb0-.07],[*a,za0-.07]])
                uv=np.array([[.216,.67],[.216,.69],[.216,.69],[.216,.67]])
                walkbuf['MAIN'].add(v[[0,1,2]],uv[[0,1,2]]);walkbuf['MAIN'].add(v[[0,2,3]],uv[[0,2,3]])
        pavementbuf=Buffer();surface(pavement,pavementbuf,-.008)
        pavementbuf.save(args.out/'pavement_continuous.npz')
        for reg,b in roadbuf.items():b.save(args.out/f'roads_{reg}.npz')
        for reg,b in walkbuf.items():b.save(args.out/f'sidewalks_{reg}.npz')
        print('SOURCE_MESHES_ASSEMBLED',roadtriangles,walktriangles,'corner_area',round(corners.area,2),flush=True)
    else:
        required=['pavement_continuous.npz']+[f'{kind}_{reg}.npz' for kind in ['roads','sidewalks'] for reg in ['MAIN','WEST','EAST','BRIDGES']]
        assert all((args.out/p).is_file() for p in required),'Incomplete source-mesh checkpoint'
        print('SOURCE_MESHES_REUSED',flush=True)
    # Remove only placeholder boxes encroaching on the revised road boundary.
    buildings=[];removed=0;building_exclusion=full.buffer(3)
    shapely.prepare(building_exclusion)
    for b in baseline['buildings']:
        cx,cy=b['center'];sx,sy,h=b['size'];fp=box(cx-sx/2,cy-sy/2,cx+sx/2,cy+sy/2)
        if building_exclusion.intersects(fp):
            removed+=1;continue
        b=dict(b);cc=np.array(fp.exterior.coords);b['base']=float(np.max(terrainz(cc)));buildings.append(b)
    # Terrain uses the exact same filled footprint as the output pavement and
    # sidewalks, with a small covered overlap rather than visible black cracks.
    cutter=full.buffer(-.045)
    for reg,poly0 in ISLANDS.items():
        poly=poly0.difference(lake) if reg=='WEST' else poly0
        domain=poly.difference(cutter)
        pointparts=[];keep=[];offset=0
        for parcel in shapely.get_parts(domain):
            if parcel.geom_type!='Polygon' or parcel.area<.0001:continue
            boundarypoints=np.vstack(list(rings(dense_polygon(parcel,5))))
            minx,miny,maxx,maxy=parcel.bounds
            xx,yy=np.meshgrid(np.arange(minx,maxx,12),np.arange(miny,maxy,12));pts=np.c_[xx.ravel(),yy.ravel()]
            pts=pts[shapely.contains_xy(parcel,pts[:,0],pts[:,1])]
            pts=np.unique(np.round(np.vstack([pts,boundarypoints]),5),axis=0)
            if len(pts)<3:continue
            try:tri=Delaunay(pts)
            except Exception:continue
            polygons=shapely.polygons(pts[tri.simplices]);shapely.prepare(parcel)
            mask=shapely.covers(parcel,polygons);faces=tri.simplices[mask].tolist()
            touched=(~mask)&shapely.intersects(parcel,polygons)
            fragments=shapely.intersection(polygons[touched],parcel)
            more=shapely.get_parts(shapely.constrained_delaunay_triangles(fragments));more=more[~shapely.is_empty(more)]
            lookup={tuple(p):i for i,p in enumerate(pts)};extra=[]
            for t in more:
                indices=[]
                for p in np.array(t.exterior.coords)[:3]:
                    key=tuple(np.round(p,5))
                    if key not in lookup:lookup[key]=len(pts)+len(extra);extra.append(key)
                    indices.append(lookup[key])
                faces.append(indices)
            if extra:pts=np.vstack([pts,extra])
            pointparts.append(pts);keep.extend((np.array(faces)+offset).tolist());offset+=len(pts)
        points=np.vstack(pointparts)
        z=terrainz(points)
        coast=shapely.distance(shapely.points(points),poly0.boundary);z=2.3+(z-2.3)*smoothstep(coast/25)
        for b in buildings:
            if b['region']!=reg:continue
            cx,cy=b['center'];sx,sy,_=b['size'];d=np.maximum(np.abs(points[:,0]-cx)-sx/2,np.abs(points[:,1]-cy)-sy/2);w=1-smoothstep(np.maximum(d,0)/5);z=z*(1-w)+(b['base']-.12)*w
        np.savez_compressed(args.out/f'terrain_{reg}.npz',vertices=np.c_[points,z].astype(np.float32),faces=np.array(keep,np.int32),coast=np.array(poly0.exterior.coords,np.float32))
        print('TERRAIN_REBUILT',reg,len(points),len(keep),flush=True)
    # Small GeoJSON sidecars make independent coverage/continuity validation
    # possible without relying on summary counts written by this generator.
    (args.out/'surface_footprints.json').write_text(json.dumps({'pavement':shapely.to_geojson(pavement),'sidewalks':shapely.to_geojson(walkarea),'full':shapely.to_geojson(full)},separators=(',',':')))
    result=dict(baseline)
    for e in edges:e.pop('line',None)
    for n in nodes:n['xy']=[float(v) for v in n['xy']]
    result.update(schema='hero13.city.blockout.v2',nodes=nodes,edges=edges,buildings=buildings,junctions=[])
    stats={'map_size_m':[4000,4000],'road_length_m':sum(e['length'] for e in edges),'routes':len({e['name'] for e in edges}),'road_edges':len(edges),'junctions':sum(len(n['edges'])>=3 for n in nodes),'buildings':len(buildings),'connected_components':len(components(nodes,edges)),'maximum_road_grade':max(e['max_grade'] for e in edges),'road_surface_height_range_m':[float(height.min()),float(height.max())],'sidewalk_width_m':WALK_WIDTH,'sidewalk_area_m2':walkarea.area,'pavement_components':1,'reconnected_street_ends':stitched,'removed_encroaching_placeholders':removed,'source_sidewalk_object':assets['sidewalk']['source_object']}
    result['stats']=stats;result['repairs']={'continuous_footprint':True,'native_longitudinal_road_scale':True,'source_sidewalk_geometry':True}
    (args.out/'city_plan.json').write_text(json.dumps(result,separators=(',',':')))
    print('OPTIMIZATION_COMPLETE',json.dumps(stats,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--templates',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reuse-source-meshes',action='store_true',help='Resume only with geometry from the same baseline/template inputs')
    main(ap.parse_args())
