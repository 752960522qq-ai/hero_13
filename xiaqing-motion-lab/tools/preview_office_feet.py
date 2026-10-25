"""Export actual animated replacement feet and remaining lower legs for QA."""
from footwear_glb import *
body,bb=load(ROOT/'dist/assets/xiaqing_native_animated.glb');shoe,sb=load(ASSET/'office_feet_rigged.glb');cfg=json.loads((ASSET/'office_feet.json').read_text());names={n.get('name'):i for i,n in enumerate(body['nodes'])};bp=body['meshes'][0]['primitives'][0];original=acc(body,bb,bp['attributes']['POSITION']);tri=acc(body,bb,bp['indices']).reshape(-1,3)
for name,t in [('Idle',0),('Walk',.3),('Run',.18)]:
 anim=next(x for x in body['animations'] if x['name']==name);w=posed_world(body,bb,anim,t);pv,pn=skin_points(body,bb,bp,w);pv[:,1]+=LIFT
 q=copy.deepcopy(body);bin=bytearray(bb);q['nodes']=[{'name':'Feet_QA','mesh':0}];q['meshes']=[copy.deepcopy(body['meshes'][0])];q['scenes']=[{'nodes':[0]}];q['scene']=0;q.pop('skins',None);q.pop('animations',None);pr=q['meshes'][0]['primitives'][0];pr['attributes']={'POSITION':append(q,bin,pv,'VEC3'),'NORMAL':append(q,bin,pn,'VEC3'),'TEXCOORD_0':pr['attributes']['TEXCOORD_0']};keep=(original[tri,1]<.35).all(1);keep[cfg['mask']['hideTriangles']]=False;pr['indices']=append(q,bin,tri[keep].ravel(),'SCALAR',5125);save(q,bin,f'/tmp/office_{name}_body.glb')
 q=copy.deepcopy(shoe);bin=bytearray(sb);sw={i:w[names[n['name']]] for i,n in enumerate(shoe['nodes']) if n.get('name') in names};meshes=[]
 for mesh in shoe['meshes']:
  mesh=copy.deepcopy(mesh);pr=mesh['primitives'][0];pv,pn=skin_points(shoe,sb,pr,sw);pv[:,1]+=LIFT;pr['attributes']={'POSITION':append(q,bin,pv,'VEC3'),'NORMAL':append(q,bin,pn,'VEC3'),'TEXCOORD_0':pr['attributes']['TEXCOORD_0']};meshes.append(mesh)
 q['meshes']=meshes;q['nodes']=[{'name':m['name'],'mesh':i} for i,m in enumerate(meshes)];q['scenes']=[{'nodes':list(range(len(meshes)))}];q['scene']=0;q.pop('skins',None);save(q,bin,f'/tmp/office_{name}_shoe.glb')
 print(name,'exported')
