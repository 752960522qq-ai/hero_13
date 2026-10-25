"""Prepare garment fitting data for Blender; source texture and UVs are retained."""
import sys,json,shutil
import numpy as np
from scipy.spatial import cKDTree
from glb_shoe_utils import ROOT,load,acc,evaluate,R
SOURCE=ROOT/'source-models/shirt_trouser_original.glb'
if not SOURCE.exists():shutil.copyfile('/workspace/attachments/4678464b-5262-482d-abe4-71e137a4bbcf/shirt+trouser.glb',SOURCE)
s,sb=load(SOURCE);p=s['meshes'][0]['primitives'][0];a=p['attributes'];v=acc(s,sb,a['POSITION']);uv=acc(s,sb,a['TEXCOORD_0']);f=acc(s,sb,p['indices']).reshape(-1,3)
n,nb=load(ROOT/'dist/assets/xiaqing_native_animated.glb');bp=n['meshes'][0]['primitives'][0];ba=bp['attributes'];bv=acc(n,nb,ba['POSITION']);bj=acc(n,nb,ba['JOINTS_0']);bw=acc(n,nb,ba['WEIGHTS_0']);bw/=bw.sum(1)[:,None];world=evaluate(n,nb,{'channels':[]},0);names=[n['nodes'][i]['name'] for i in n['skins'][0]['joints']];bone={n['nodes'][i]['name']:world[i][:3,3] for i in n['skins'][0]['joints']}
def smooth(x,a,b):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
# Cut at collar/neck, cuffs and trouser hems. Preserve the clothing's skin inset.
from clip_garment_edges import clip_openings
v,uv,faces=clip_openings(v,uv,f)
fit=v.copy();fit[:,0]*=1.50;fit[:,2]=fit[:,2]*1.45+np.interp(v[:,1],[.056,.30,.53,.65,.795,.845],[.123,.1285,.1005,.1225,.1123,.116])
fit[:,1]=np.interp(v[:,1],[.056,.30,.53,.65,.795,.845],[.145,.536,.95,1.15,1.3805,1.455])
for side,sign in [('l',1),('r',-1)]:
 shoulder=np.array([sign*.105,.795,-.09]);elbow=np.array([sign*.202,.695,-.05]);wrist=np.array([sign*.225,.616,.065]);sh=bone[side+'_arm_humerus'];el=bone[side+'_arm_radius'];wr=bone[side+'_arm_wrist']
 def segment(src0,src1,dst0,dst1):
  aa=src1-src0;bb=dst1-dst0;aa/=np.linalg.norm(aa);bb/=np.linalg.norm(bb);rot=R.align_vectors([bb],[aa])[0].as_matrix();return (v-src0)@rot.T*(np.linalg.norm(dst1-dst0)/np.linalg.norm(src1-src0))+dst0
 upper=segment(shoulder,elbow,sh,el);lower=segment(elbow,wrist,el,wr)
 blend=smooth(.72-v[:,1],0,.045);arm=upper*(1-blend[:,None])+lower*blend[:,None]
 amount=smooth(sign*v[:,0],.085,.15)*smooth(v[:,1],.57,.65)
 fit=fit*(1-amount[:,None])+arm*amount[:,None]
# Center each trouser hem around the native ankle, with clearance over shoe collars.
for sign in [-1,1]:
 ids=np.flatnonzero((v[:,0]*sign>0)&(v[:,1]<.30));blend=1-smooth(v[ids,1],.07,.22);fit[ids,0]+=sign*.0135*blend
 fit[ids,0]+= (fit[ids,0]-sign*.111)*(.12*blend)
 fit[ids,2]+= (fit[ids,2]+.0225)*(.12*blend)
# Transfer normalized native weights by spatial neighborhoods, separated by side.
used=np.unique(faces);weights=np.zeros((len(v),len(names)),dtype=np.float32)
for sign in [-1,1]:
 chosen=used[fit[used,0]*sign>=0];pool=np.flatnonzero(bv[:,0]*sign>=-.005);dist,ids=cKDTree(bv[pool]).query(fit[chosen],k=4);ids=pool[ids];coef=1/np.maximum(dist,.003)**4;coef/=coef.sum(1)[:,None]
 for k in range(4):
  for c in range(4):np.add.at(weights,(chosen,bj[ids[:,k],c]),coef[:,k]*bw[ids[:,k],c])
# Trouser hems belong to the shin, never the high-heel ankle rotation.
for side,sign in [('l',1),('r',-1)]:
 selected=used[(v[used,0]*sign>0)&(v[used,1]<.18)];blend=1-smooth(v[selected,1],.10,.18);weights[selected]*=(1-blend[:,None]);weights[selected,names.index(side+'_leg_tibia')]+=blend
# Region identity drives per-module visibility, but the suit equips as one unit.
config=json.loads((ROOT/'dist/assets/body-modules.json').read_text());bf=acc(n,nb,bp['indices']).reshape(-1,3);owner=np.empty(len(bf),dtype=int)
for i,m in enumerate(config['modules']):owner[m['triangles']]=i
allowed=[1,2,3,4,7,8,9,10,11];nativeFaces=np.flatnonzero(np.isin(owner,allowed));centers=bv[bf[nativeFaces]].mean(1);_,near=cKDTree(centers).query(fit[faces].mean(1));face_slots=owner[nativeFaces[near]]
# Neck is a skin-to-skin interface: snap its rim onto the original neck ring,
# copying identical weights at that boundary. Wrists/hems overlap under cuffs.
_,weld=np.unique(np.round(v,6),axis=0,return_inverse=True);wf=weld[faces];edges=np.sort(np.concatenate([wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]]),axis=1);edges,counts=np.unique(edges,axis=0,return_counts=True);rim=np.flatnonzero(np.isin(weld,np.unique(edges[counts==1])));neck=rim[v[rim,1]>.84]
# Preserve the collar surface: nearest-vertex snapping collapsed the opening.
# Extend cuffs along the forearm and hems down the shin for a small overlap.
# Smooth falloff keeps the outer garment silhouette and existing UVs intact.
for side,sign in [('l',1),('r',-1)]:
 cuff=used[(v[used,0]*sign>.15)&(v[used,1]>.615)&(v[used,1]<.645)]
 axis=bone[side+'_arm_wrist']-bone[side+'_arm_radius'];axis/=np.linalg.norm(axis)
 fade=1-smooth(v[cuff,1],.616,.645);fit[cuff]+=axis[None,:]*(.006*fade[:,None])
 hem=used[(v[used,0]*sign>0)&(v[used,1]<.09)]
 fit[hem,1]-=.005*(1-smooth(v[hem,1],.056,.09))
# Give cuffs a small radial clearance over the retained wrist surface.
for side,sign in [('l',1),('r',-1)]:
 ids=used[(v[used,0]*sign>.15)&(v[used,1]>.615)&(v[used,1]<.66)]
 axis=bone[side+'_arm_wrist']-bone[side+'_arm_radius'];axis/=np.linalg.norm(axis)
 delta=fit[ids]-bone[side+'_arm_wrist'];radial=delta-np.outer(delta@axis,axis)
 radial/=np.maximum(np.linalg.norm(radial,axis=1)[:,None],1e-8)
 fit[ids]+=radial*(.003*(1-smooth(v[ids,1],.616,.66)))[:,None]
# Fit trouser openings outside the independent replacement ankle surfaces.
for sign in [-1,1]:
 ids=used[(v[used,0]*sign>0)&(v[used,1]<.12)]
 fade=1-smooth(v[ids,1],.056,.12)
 fit[ids,1]+=.035*fade
 center=np.array([sign*.111,0,-.0225]);rad=fit[ids][:,[0,2]]-center[[0,2]]
 length=np.linalg.norm(rad,axis=1);target=np.maximum(length,.047)
 fit[ids[:,None],[0,2]]+=rad*(fade*(target/np.maximum(length,1e-8)-1))[:,None]
# The garment ends at fabric, with an even wrist-aligned cuff and shared weights.
for side,sign in [('l',1),('r',-1)]:
 ids=used[(v[used,0]*sign>.15)&(v[used,1]<.65)]
 axis=bone[side+'_arm_wrist']-bone[side+'_arm_radius'];axis/=np.linalg.norm(axis)
 fade=1-smooth(v[ids,1],.625,.65);along=(fit[ids]-bone[side+'_arm_wrist'])@axis
 fit[ids]+=axis[None,:]*((.006-along)*fade)[:,None]
 radial=fit[ids]-bone[side+'_arm_wrist'];radial-=np.outer(radial@axis,axis)
 length=np.linalg.norm(radial,axis=1);target=np.clip(length,.034,.037)
 fit[ids]+=radial*(fade*(target/np.maximum(length,1e-8)-1))[:,None]
 # Match the native wrist/twist blend; a pure wrist bone breaks the cuff in Run.
 pool=np.flatnonzero((bv[:,0]*sign>.25)&(np.linalg.norm(bv-bone[side+'_arm_wrist'],axis=1)<.08))
 dist,near=cKDTree(bv[pool]).query(fit[ids],k=4);near=pool[near];coef=1/np.maximum(dist,.003)**4;coef/=coef.sum(1)[:,None]
 wristweights=np.zeros((len(ids),len(names)),dtype=np.float32)
 for k in range(4):
  for c in range(4):np.add.at(wristweights,(np.arange(len(ids)),bj[near[:,k],c]),coef[:,k]*bw[near[:,k],c])
 weights[ids]=weights[ids]*(1-fade[:,None])+wristweights*fade[:,None]
# Protect small native skin collars at module borders; hide the actual interior.
replaced=np.concatenate([np.array(config['modules'][i]['triangles']) for i in allowed]+[np.array(config['modules'][14]['triangles'])]);bc=bv[bf].mean(1)
retain=np.zeros(len(bc),dtype=bool)
for side in ['l','r']:
 retain|=np.linalg.norm(bc-bone[side+'_arm_wrist'],axis=1)<.05
 retain|=(np.linalg.norm(bc[:,[0,2]]-bone[side+'_leg_ankle'][[0,2]],axis=1)<.075)&(bc[:,1]<.24)
hidden=replaced[~retain[replaced]]
# Hand-module classification may retain proximal forearm triangles; include them.
extra=(bc[:,1]>1.40)&(abs(bc[:,0])<.11)
for side,sign in [('l',1),('r',-1)]:
 axis=bone[side+'_arm_wrist']-bone[side+'_arm_radius'];axis/=np.linalg.norm(axis)
 delta=bc-bone[side+'_arm_wrist'];along=delta@axis
 extra|=(bc[:,0]*sign>.25)&(along<-.045)&(np.linalg.norm(delta,axis=1)<.07)
hidden=np.union1d(hidden,np.flatnonzero(extra))
order=np.argsort(weights,axis=1)[:,-4:];val=np.take_along_axis(weights,order,axis=1);val/=np.maximum(val.sum(1)[:,None],1e-12)
np.savez('/tmp/shirt-fit.npz',positions=fit,uv=uv,faces=faces,joints=order,weights=val,face_slots=face_slots,bone_world=np.array([world[i] for i in n['skins'][0]['joints']]))
meta={'boneNames':names,'slots':[{ 'id':m['id'],'label':m['label']} for m in config['modules']], 'asset':'./assets/wardrobe/shirt_trouser_rigged.glb','hideTriangles':hidden.tolist(),'positionCount':len(bv),'source':str(SOURCE)}
(ROOT/'dist/assets/wardrobe/shirt_trouser.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
print('fitted vertices',len(used),'triangles',len(faces),'neck rim',len(neck))
