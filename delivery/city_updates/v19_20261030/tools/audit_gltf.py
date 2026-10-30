"""Inspect supplied GLBs without changing their bytes."""
from pathlib import Path
import json,struct,io,collections,hashlib
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work_v19/audit'; OUT.mkdir(parents=True,exist_ok=True)
sources=[]
for si,p in enumerate(sorted((ROOT/'upload').glob('*.glb')),1):
    data=p.read_bytes(); n=struct.unpack_from('<I',data,12)[0]; d=json.loads(data[20:20+n]); binary=data[28+n:]
    nodes=d.get('nodes',[]); parent={j:i for i,x in enumerate(nodes) for j in x.get('children',[])}
    mats={};bounds={}
    def transform(i):
        if i in mats:return mats[i]
        x=nodes[i]
        if 'matrix' in x:m=np.array(x['matrix']).reshape(4,4).T
        else:
            q=x.get('rotation',[0,0,0,1]); a,b,c,w=q
            m=np.eye(4);m[:3,:3]=np.array([[1-2*b*b-2*c*c,2*a*b-2*c*w,2*a*c+2*b*w],[2*a*b+2*c*w,1-2*a*a-2*c*c,2*b*c-2*a*w],[2*a*c-2*b*w,2*b*c+2*a*w,1-2*a*a-2*b*b]])@np.diag(x.get('scale',[1,1,1]));m[:3,3]=x.get('translation',[0,0,0])
        if i in parent:m=transform(parent[i])@m
        mats[i]=m;return m
    def bbox(i):
        if i in bounds:return bounds[i]
        x=nodes[i];bs=[]
        if 'mesh' in x:
            for pr in d['meshes'][x['mesh']]['primitives']:
                a=d['accessors'][pr['attributes']['POSITION']]
                if 'min' in a:
                    lo,hi=a['min'],a['max'];pts=np.array([[xx,yy,zz,1] for xx in [lo[0],hi[0]] for yy in [lo[1],hi[1]] for zz in [lo[2],hi[2]]])@transform(i).T;bs.append([pts[:,:3].min(0),pts[:,:3].max(0)])
        for j in x.get('children',[]):
            b=bbox(j)
            if b is not None:bs.append(b)
        bounds[i]=np.array([np.min(np.array(bs)[:,0],axis=0),np.max(np.array(bs)[:,1],axis=0)]) if bs else None
        return bounds[i]
    for i in range(len(nodes)):bbox(i)
    records=[]
    for i,x in enumerate(nodes):
        if bounds[i] is None:continue
        b=bounds[i]; depth=0;j=i
        while j in parent:depth+=1;j=parent[j]
        records.append(dict(index=i,name=x.get('name',''),parent=parent.get(i),depth=depth,mesh=x.get('mesh'),children=len(x.get('children',[])),bounds=b.round(4).tolist(),size=(b[1]-b[0]).round(4).tolist()))
    images=[]
    for k,x in enumerate(d.get('images',[])):
        if 'bufferView' not in x:continue
        v=d['bufferViews'][x['bufferView']]; bb=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
        im=Image.open(io.BytesIO(bb));images.append(dict(index=k,name=x.get('name',''),size=list(im.size),bytes=len(bb)))
    source=dict(id=f'S{si:02}',file=p.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),nodes=len(nodes),meshes=len(d.get('meshes',[])),images=images,records=records)
    (OUT/f'S{si:02}_hierarchy.json').write_text(json.dumps(source,ensure_ascii=False,indent=2));sources.append({k:v for k,v in source.items() if k!='records'})
    print(source['id'],p.name,'roots',[(r['index'],r['name'],r['size']) for r in records if r['depth']<=4][:12],flush=True)
(OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
