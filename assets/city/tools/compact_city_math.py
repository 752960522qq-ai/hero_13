"""Metric reconstruction utilities. Coasts are fresh control polygons, not scaled v7."""
import sys,math
from pathlib import Path
import numpy as np
try:import shapely
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'work/compact_city/deps'))
    import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

def smoothstep(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def curve(points,closed=False,step=4):
    p=np.asarray(points,float)
    if closed and np.linalg.norm(p[0]-p[-1])>1e-6:p=np.vstack([p,p[0]])
    ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    cs=CubicSpline(ds,p,bc_type='periodic' if closed else 'natural')
    return cs(np.linspace(0,ds[-1],max(2,int(ds[-1]/step)+1)))

def coasts():
    controls={
      'MAIN':[(-1200,250),(-1120,660),(-950,1050),(-720,1360),(-350,1570),(50,1480),(430,1510),(820,1380),(1150,1090),(1380,780),(1410,440),(1240,150),(900,-20),(520,15),(150,-100),(-250,-60),(-680,40)],
      'WEST':[(-1690,-560),(-1380,-390),(-1030,-440),(-720,-620),(-430,-910),(-430,-1220),(-690,-1490),(-1040,-1620),(-1420,-1500),(-1690,-1190)],
      'EAST':[(280,-740),(510,-520),(850,-460),(1180,-530),(1470,-730),(1650,-1050),(1500,-1390),(1180,-1590),(830,-1660),(530,-1480),(340,-1160)]}
    lake=Polygon(curve([(-1250,-750),(-1100,-710),(-980,-810),(-960,-960),(-1090,-1050),(-1230,-960)],True))
    targets={'MAIN':3550000.,'WEST':1120000.,'EAST':1130000.};out={}
    for k,cp in controls.items():
        p=Polygon(curve(cp,True));lo,hi=-200.,200.
        for _ in range(55):
            mid=(lo+hi)/2;q=p.buffer(mid,quad_segs=8)
            area=q.difference(lake).area if k=='WEST' else q.area
            if area<targets[k]:lo=mid
            else:hi=mid
        out[k]=p.buffer((lo+hi)/2,quad_segs=8)
    return out,lake

def raw_height(xy,islands,lake):
    p=np.asarray(xy).reshape(-1,2);x,y=p.T;z=np.full(len(p),-4.)
    for k,poly in islands.items():
        # Terrain boundary vertices are quantized when meshed; centimetre tolerance
        # prevents microscopic outward rounding from sampling the sea-floor height.
        ids=shapely.intersects_xy(poly.buffer(.02),x,y)
        xx=x[ids];yy=y[ids]
        if k=='MAIN':h=9+23*np.exp(-((xx+650)/670)**2-((yy-1220)/650)**2)+13*np.exp(-((xx-940)/650)**2-((yy-1040)/650)**2)
        elif k=='WEST':h=10+25*np.exp(-((xx+1470)/620)**2-((yy+680)/650)**2)
        else:h=8+9*np.exp(-((xx-600)/650)**2-((yy+1100)/680)**2)
        d=shapely.distance(shapely.points(p[ids]),poly.boundary)
        zz=3+(h-3)*smoothstep(d/500)
        if k=='WEST':
            dl=shapely.distance(shapely.points(p[ids]),lake);w=1-smoothstep(dl/65);zz=zz*(1-w)+10*w
        z[ids]=zz
    return z

class SurfaceProjector:
    def __init__(self,edges):
        pp=[np.asarray(e['points'],float) for e in edges]
        self.a=np.concatenate([p[:-1] for p in pp]);self.b=np.concatenate([p[1:] for p in pp]);self.d=self.b-self.a
        self.w=np.concatenate([np.full(len(p)-1,e['width']/2) for p,e in zip(pp,edges)])
        self.tree=cKDTree((self.a[:,:2]+self.b[:,:2])/2)
    def project(self,xy):
        p=np.asarray(xy).reshape(-1,2);_,ids=self.tree.query(p,k=min(12,len(self.a)))
        d=self.d[ids,:2];t=np.clip(np.sum((p[:,None]-self.a[ids,:2])*d,axis=-1)/np.maximum(np.sum(d*d,axis=-1),1e-10),0,1)
        q=self.a[ids,:2]+d*t[:,:,None];dist=np.linalg.norm(p[:,None]-q,axis=-1);ch=dist.argmin(1);ii=ids[np.arange(len(p)),ch];tt=t[np.arange(len(p)),ch]
        return dist[np.arange(len(p)),ch],self.w[ii],self.a[ii,2]+self.d[ii,2]*tt,ii,tt
    def height(self,xy):return self.project(xy)[2]

def terrain_height(xy,islands,lake,projector):
    p=np.asarray(xy).reshape(-1,2);h=raw_height(p,islands,lake);d,w,z,_,_=projector.project(p)
    t=1-smoothstep((d-w)/np.maximum(36,np.abs(z-h)*5));return h*(1-t)+(z-.075)*t

def frame(edge,s):
    p=np.asarray(edge['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
    ss=np.clip(np.asarray(s),0,ds[-1]);q=np.stack([np.interp(ss,ds,p[:,i]) for i in range(3)],axis=-1)
    tangent=np.gradient(p[:,:2],ds,axis=0);tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-8)
    t=np.stack([np.interp(ss,ds,tangent[:,i]) for i in range(2)],axis=-1);t/=np.maximum(np.linalg.norm(t,axis=-1,keepdims=True),1e-8)
    return q,np.stack([-t[...,1],t[...,0]],axis=-1)
