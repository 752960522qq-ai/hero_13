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
      'MAIN':[(-950,170),(-930,510),(-830,840),(-650,1080),(-340,1240),(40,1230),(420,1190),(760,1040),(1010,790),(1060,510),(940,220),(650,40),(300,-40),(-100,-100),(-500,-10)],
      'WEST':[(-1350,-480),(-1120,-300),(-800,-330),(-530,-500),(-470,-780),(-650,-1030),(-960,-1160),(-1250,-960),(-1400,-720)],
      'EAST':[(180,-550),(450,-320),(770,-340),(1080,-530),(1240,-800),(1060,-1110),(740,-1220),(420,-1100),(220,-850)]}
    lake=Polygon(curve([(-1100,-580),(-990,-535),(-875,-605),(-880,-740),(-1000,-805),(-1110,-725)],True))
    targets={'MAIN':2050000.,'WEST':580000.,'EAST':620000.};out={}
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
        if k=='MAIN':h=10+23*np.exp(-((xx+500)/510)**2-((yy-970)/500)**2)+14*np.exp(-((xx-670)/470)**2-((yy-850)/460)**2)
        elif k=='WEST':h=10+23*np.exp(-((xx+1170)/440)**2-((yy+540)/460)**2)
        else:h=8+10*np.exp(-((xx-540)/490)**2-((yy+820)/500)**2)
        d=shapely.distance(shapely.points(p[ids]),poly.boundary)
        zz=3+(h-3)*smoothstep(d/340)
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
