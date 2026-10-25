import json,sys,numpy as np
from glb_shoe_utils import ROOT,load,acc,evaluate
j,b=load(ROOT/'dist/assets/xiaqing_native_animated.glb');p=j['meshes'][0]['primitives'][0];a=p['attributes'];v=acc(j,b,a['POSITION']);ids=acc(j,b,a['JOINTS_0']);weights=acc(j,b,a['WEIGHTS_0']);faces=acc(j,b,p['indices']).reshape(-1,3);names=[j['nodes'][i]['name'] for i in j['skins'][0]['joints']]
slots=[('head','头'),('upper_arm_l','左大臂'),('upper_arm_r','右大臂'),('forearm_l','左小臂'),('forearm_r','右小臂'),('hand_l','左手'),('hand_r','右手'),('torso','身体'),('thigh_l','左大腿'),('thigh_r','右大腿'),('calf_l','左小腿'),('calf_r','右小腿'),('foot_l','左脚'),('foot_r','右脚'),('penis','阴茎与睾丸')]
def group(n):
 for side in ['l','r']:
  if n.startswith(side+'_hand') or n==side+'_arm_wrist':return 'hand_'+side
  if n.startswith(side+'_arm_radius'):return 'forearm_'+side
  if n.startswith(side+'_arm_humerus') or n.startswith(side+'_delt'):return 'upper_arm_'+side
  if n.startswith(side+'_leg_ankle') or n.startswith(side+'_leg_ball'):return 'foot_'+side
  if n.startswith(side+'_leg_tibia'):return 'calf_'+side
  if n.startswith(side+'_leg_femur') or n.startswith(side+'_leg_thigh'):return 'thigh_'+side
 return 'torso'
keys=[x[0] for x in slots];boneGroup=np.array([keys.index(group(n)) for n in names]);scores=np.zeros((len(v),15))
for k in range(4):np.add.at(scores,(np.arange(len(v)),boneGroup[ids[:,k]]),weights[:,k])
owner=scores[faces].sum(1).argmax(1);center=v[faces].mean(1)
# Only the neck junction belongs to the head; shoulder caps stay with torso/arms.
owner[(center[:,1]>1.435)&(np.abs(center[:,0])<.07)]=0
# Native mesh has no separate genital bone; isolate its central protruding geometry.
mask=(np.abs(center[:,0])<.065)&(center[:,1]>.68)&(center[:,1]<.99)&(center[:,2]>.12)
# Include the scrotal sac and its root, while excluding the lateral thighs.
scrotum=(np.abs(center[:,0])<.052)&(center[:,1]>.805)&(center[:,1]<.925)&(center[:,2]>np.where(center[:,1]<.89,-.035,.015))
owner[mask|scrotum]=14
out={'bodyMesh':'pl2020_Skin_Mat','positionCount':len(v),'triangleCount':len(faces),'modules':[{'id':key,'label':label,'triangles':np.flatnonzero(owner==i).tolist()} for i,(key,label) in enumerate(slots)],'boundaryMethod':'bone weights; anatomical bounds for head and genital region'}
assert sum(len(m['triangles']) for m in out['modules'])==len(faces)
(ROOT/'dist/assets/body-modules.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
print({m['id']:len(m['triangles']) for m in out['modules']})
