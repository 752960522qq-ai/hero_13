"""Replace feet while equipped; shared native skeleton, exact native seam vertices."""
import io,copy,json,hashlib
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from footwear_glb import *
# Supplied asset is a RIGHT foot. Start with the Blender-mirrored LEFT template.
SOURCE=ROOT/'source-models/office_high_heel_left.glb'
CUT_BODY=.17;CUT_SOURCE=.82

def closest(points,positions,triangles):
 triangles=np.asarray(triangles);t=positions[triangles];tree=cKDTree(t.mean(1));_,cand=tree.query(points,k=8);a=t[cand,0];ab=t[cand,1]-a;ac=t[cand,2]-a;p=points[:,None,:]-a
 d00=(ab*ab).sum(2);d01=(ab*ac).sum(2);d11=(ac*ac).sum(2);d20=(p*ab).sum(2);d21=(p*ac).sum(2);den=np.maximum(d00*d11-d01*d01,1e-18)
 v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den;bary=np.stack([1-v-w,v,w],2)
 pos=(t[cand]*bary[:,:,:,None]).sum(2);dist=((pos-points[:,None,:])**2).sum(2);dist[(bary<0).any(2)]=np.inf
 for u,z in [(0,1),(1,2),(2,0)]:
  aa=t[cand,u];e=t[cand,z]-aa;q=np.clip(((points[:,None,:]-aa)*e).sum(2)/np.maximum((e*e).sum(2),1e-18),0,1);d=((aa+e*q[:,:,None]-points[:,None,:])**2).sum(2);better=d<dist;new=np.zeros_like(bary);new[:,:,u]=1-q;new[:,:,z]=q;bary[better]=new[better];dist[better]=d[better]
 k=dist.argmin(1);return triangles[cand[np.arange(len(points)),k]],bary[np.arange(len(points)),k]

def clip_source(v,n,uv,tri):
 verts=[];norm=[];tex=[];faces=[]
 for face in tri:
  poly=[(v[i],n[i],uv[i]) for i in face];out=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   inside=a[0][1]<=CUT_SOURCE;other=b[0][1]<=CUT_SOURCE
   if inside:out.append(a)
   if inside!=other:
    f=(CUT_SOURCE-a[0][1])/(b[0][1]-a[0][1]);out.append(tuple(x+(y-x)*f for x,y in zip(a,b)))
  if len(out)<3:continue
  start=len(verts)
  for a,b,c in out:verts.append(a);norm.append(b);tex.append(c)
  for k in range(1,len(out)-1):faces.append([start,start+k,start+k+1])
 return np.array(verts),np.array(norm),np.array(tex),np.array(faces)

def build():
 body,bb=load(ROOT/'dist/assets/xiaqing_native_animated.glb');bp=body['meshes'][0]['primitives'][0];bv=acc(body,bb,bp['attributes']['POSITION']);bn=acc(body,bb,bp['attributes']['NORMAL']);bu=acc(body,bb,bp['attributes']['TEXCOORD_0']);bt=acc(body,bb,bp['indices']).reshape(-1,3);bj=acc(body,bb,bp['attributes']['JOINTS_0']);bw=acc(body,bb,bp['attributes']['WEIGHTS_0'])
 world=posed_world(body,bb);pv,pn=skin_points(body,bb,bp,world);skin=body['skins'][0];bones=skin['joints'];names={body['nodes'][i]['name']:k for k,i in enumerate(bones)};ib=acc(body,bb,skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);sm=np.array([world[i]@m for i,m in zip(bones,ib)])
 src,sb=load(SOURCE);sp=src['meshes'][0]['primitives'][0];sv=acc(src,sb,sp['attributes']['POSITION']);sn=acc(src,sb,sp['attributes']['NORMAL']);su=acc(src,sb,sp['attributes']['TEXCOORD_0']);st=acc(src,sb,sp['indices']).reshape(-1,3)
 v,n,uv,tr=clip_source(sv,sn,su,st);im=src['images'][src['textures'][0]['source']];view=src['bufferViews'][im['bufferView']];img=Image.open(io.BytesIO(sb[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGB');pix=np.asarray(img);sample=uv[tr].mean(1);rgb=pix[np.clip((sample[:,1]*img.height).astype(int),0,img.height-1),np.clip((sample[:,0]*img.width).astype(int),0,img.width-1)]/255
 # Skin is the light warm region; black upper/red sole retain original material/UV.
 skinface=(rgb[:,0]>.32)&(rgb[:,1]>.20)&(rgb[:,2]>.14)
 hide=(bv[bt,1]<CUT_BODY).any(1);hidden=np.flatnonzero(hide).tolist()
 unique,uid,inv=np.unique(np.round(bv,6),axis=0,return_index=True,return_inverse=True)
 edges=lambda a:set(map(tuple,np.sort(np.concatenate([a[:,[0,1]],a[:,[1,2]],a[:,[2,0]]]),axis=1)))
 boundary=np.array(list(edges(inv[bt[hide]])&edges(inv[bt[~hide]])))
 out={'asset':{'version':'2.0','generator':'Xiaqing complete-foot wardrobe'},'buffers':[],'bufferViews':[],'accessors':[],'nodes':[],'meshes':[],'skins':[],'materials':[],'images':[],'textures':[],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}]};data=bytearray()
 def imagecopy(j,b,index):
  im=j['images'][j['textures'][index]['source']];view=j['bufferViews'][im['bufferView']];raw=b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];data.extend(b'\0'*(-len(data)%4));vi=len(out['bufferViews']);out['bufferViews'].append({'buffer':0,'byteOffset':len(data),'byteLength':len(raw)});data.extend(raw);ii=len(out['images']);out['images'].append({'bufferView':vi,'mimeType':im['mimeType']});ti=len(out['textures']);out['textures'].append({'source':ii,'sampler':0});return ti
 shoeMat=copy.deepcopy(src['materials'][0]);shoeMat['name']='OfficeHeel_Black';shoeMat['pbrMetallicRoughness']['baseColorTexture']['index']=imagecopy(src,sb,0);out['materials'].append(shoeMat)
 skinMat=copy.deepcopy(body['materials'][bp['material']]);skinMat['name']='OfficeFoot_NativeSkin';skinMat['pbrMetallicRoughness']['baseColorTexture']['index']=imagecopy(body,bb,0);skinMat['normalTexture']['index']=imagecopy(body,bb,1);out['materials'].append(skinMat)
 rest=evaluate(body,bb,{'channels':[]},0)
 for i in bones:out['nodes'].append({'name':body['nodes'][i]['name'],'matrix':rest[i].T.ravel().tolist()})
 out['skins']=[{'joints':list(range(len(bones))),'inverseBindMatrices':append(out,data,ib.transpose(0,2,1).reshape(-1,16),'MAT4')}]
 seamchecks=[]
 for side,sign in [('L',1),('R',-1)]:
  foottri=bt[(bv[bt,1]<.30).all(1)&(bv[bt,0]*sign>.02).all(1)]
  be=boundary[(unique[boundary,0]*sign>0).all(1)];ringids=uid[np.unique(be)];ring=pv[ringids];center=ring[:,[0,2]].mean(0)
  # Match upper ankle shape smoothly; lower foot keeps the supplied silhouette.
  fit=np.c_[sign*(v[:,0]*.28+.108),v[:,1]*.27+.005-LIFT,v[:,2]*.27+.010]
  topids=np.flatnonzero(abs(v[:,1]-CUT_SOURCE)<1e-6);topcenter=fit[topids][:,[0,2]].mean(0);theta=np.arctan2(fit[:,2]-topcenter[1],fit[:,0]-topcenter[0]);rt=np.arctan2(ring[:,2]-center[1],ring[:,0]-center[0]);order=np.argsort(rt);rt=rt[order];rr=np.linalg.norm(ring[order][:,[0,2]]-center,axis=1)
  radius=np.interp(theta,np.r_[rt[-1]-2*np.pi,rt,rt[0]+2*np.pi],np.r_[rr[-1],rr,rr[0]])
  target=center+np.c_[np.cos(theta),np.sin(theta)]*radius[:,None];blend=smooth(v[:,1],.60,CUT_SOURCE)[0];fit[:,[0,2]]=fit[:,[0,2]]*(1-blend[:,None])+target*blend[:,None]
  near,bary=closest(fit,pv,foottri);skinuv=(bu[near]*bary[:,:,None]).sum(1);nearweights=np.zeros((len(fit),len(bones)))
  for a in range(3):
   for k in range(4):np.add.at(nearweights,(np.arange(len(fit)),bj[near[:,a],k]),bary[:,a]*bw[near[:,a],k])
  toe=smooth(fit[:,2],.015,.075)[0]*(1-smooth(fit[:,1],.045,.10)[0]);base=np.zeros_like(nearweights);base[:,names[f'{side.lower()}_leg_ankle']]=1-toe;base[:,names[f'{side.lower()}_leg_ball']]=toe
  upper=smooth(fit[:,1],.075,.145)[0];allw=base*(1-upper[:,None])+nearweights*upper[:,None];js=np.argsort(allw,axis=1)[:,-4:];ws=np.take_along_axis(allw,js,axis=1);ws/=ws.sum(1,keepdims=True)
  matrices=sum(ws[:,k,None,None]*sm[js[:,k]] for k in range(4));restv=np.einsum('nij,nj->ni',np.linalg.inv(matrices),np.c_[fit,np.ones(len(fit))])[:,:3]
  # Native material on skin only. Use source normals below ankle, native normals at seam.
  nn=n/np.array([.28,.27,.27]);nn[:,0]*=sign;nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-9);matched=(pn[near]*bary[:,:,None]).sum(1);nn=nn*(1-blend[:,None])+matched*blend[:,None];nn=np.einsum('nij,nj->ni',np.linalg.inv(matrices[:,:3,:3]),nn);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-9)
  faces=tr.copy()
  if sign<0:faces=faces[:,[0,2,1]]
  # Stitch the cut new-foot ring to the exact original leg vertices, with copied weights.
  _,ii=np.unique(np.round(fit[topids],7),axis=0,return_index=True);lo=topids[ii];la=np.mod(np.arctan2(fit[lo,2]-center[1],fit[lo,0]-center[0]),2*np.pi);lo=lo[np.argsort(la)];la=np.sort(la)
  ha=np.mod(np.arctan2(ring[:,2]-center[1],ring[:,0]-center[0]),2*np.pi);o=np.argsort(ha);ringids=ringids[o];ha=ha[o];offset=len(restv);restv=np.vstack([restv,bv[ringids]]);nn=np.vstack([nn,bn[ringids]]);js=np.vstack([js,bj[ringids]]);ws=np.vstack([ws,bw[ringids]]);skinuv=np.vstack([skinuv,bu[ringids]]);uvside=np.vstack([uv,bu[ringids]])
  # Start both loops at angle zero, then advance whichever next vertex comes first.
  seam=[];i=j0=0
  while i<len(lo) or j0<len(ringids):
   li=lo[i%len(lo)];hi=offset+j0%len(ringids);ln=la[(i+1)%len(lo)]+(2*np.pi if i+1>=len(lo) else 0) if i<len(lo) else np.inf;hn=ha[(j0+1)%len(ringids)]+(2*np.pi if j0+1>=len(ringids) else 0) if j0<len(ringids) else np.inf
   if ln<hn:seam.append([li,lo[(i+1)%len(lo)],hi]);i+=1
   else:seam.append([li,offset+(j0+1)%len(ringids),hi]);j0+=1
  seam=np.array(seam);ref=np.vstack([fit,pv[ringids]]);cross=np.cross(ref[seam[:,1]]-ref[seam[:,0]],ref[seam[:,2]]-ref[seam[:,0]]);outward=ref[seam].mean(1)-np.array([center[0],0,center[1]]);outward[:,1]=0;flip=(cross*outward).sum(1)<0;seam[flip]=seam[flip][:,[0,2,1]]
  attrs={'POSITION':append(out,data,restv,'VEC3'),'NORMAL':append(out,data,nn,'VEC3'),'JOINTS_0':append(out,data,js,'VEC4',5123),'WEIGHTS_0':append(out,data,ws,'VEC4')}
  for mat,label,ff,tex in [(0,'OfficeHeel',faces[~skinface],uvside),(1,'OfficeFootSkin',np.vstack([faces[skinface],seam]),skinuv)]:
   at=dict(attrs);at['TEXCOORD_0']=append(out,data,tex,'VEC2');mi=len(out['meshes']);out['meshes'].append({'name':label+'_'+side,'primitives':[{'attributes':at,'indices':append(out,data,ff.ravel(),'SCALAR',5125),'material':mat,'mode':4}]});out['nodes'].append({'name':label+'_'+side,'mesh':mi,'skin':0})
  seamchecks.append({'side':side,'newRingVertices':len(lo),'nativeRingVertices':len(ringids),'nativeIndices':ringids.tolist(),'accessoryIndices':list(range(offset,offset+len(ringids)))})
 out['scenes']=[{'nodes':list(range(len(out['nodes'])))}];out['scene']=0
 config={'id':'office_complete_feet','slot':'shoes','mode':'replace_feet','name':'黑色高跟鞋（整脚）','asset':'./assets/wardrobe/office_feet_rigged.glb','bodyAsset':'xiaqing_native_animated.glb','bodySHA256':hashlib.sha256((ROOT/'dist/assets/xiaqing_native_animated.glb').read_bytes()).hexdigest(),'ankleDegrees':ANGLE,'ballDegrees':-ANGLE,'rootLift':LIFT,'boneNames':[body['nodes'][i]['name'] for i in bones],'meshCount':4,'mask':{'mesh':'pl2020_Skin_Mat','positionCount':len(bv),'hideTriangles':hidden},'geometryFit':{'positions':[],'normals':[]},'seams':seamchecks,'source':SOURCE.name}
 save(out,data,ASSET/'office_feet_rigged.glb');(ASSET/'office_feet.json').write_text(json.dumps(config,ensure_ascii=False,separators=(',',':')))
 print(json.dumps({'sourceFaces':len(tr),'skinFaces':int(skinface.sum()),'shoeFaces':int((~skinface).sum()),'hiddenBodyTriangles':len(hidden),'assetBytes':len(data),'seams':[{k:v for k,v in x.items() if k not in ['nativeIndices','accessoryIndices']} for x in seamchecks]}))
if __name__=='__main__':build()
