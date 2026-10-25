import bpy,bmesh,json,numpy as np
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend');rig=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];bm=bmesh.new();bm.from_mesh(o.data)
report={'character':'夏晴_牛仔裤','bones':len(rig.data.bones),'open_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'actions':{}}
assert report['open_edges']==0 and report['nonmanifold_edges']==0;bm.free()
for v in o.data.vertices:
 w=[g.weight for g in v.groups if g.weight>1e-7];assert w and len(w)<=4 and abs(sum(w)-1)<1e-5
for action in bpy.data.actions:
 rig.animation_data.action=action;start,end=map(int,action.frame_range);frames=sorted(set([start,end]+[round(start+(end-start)*i/10) for i in range(11)]));bounds=[]
 for f in frames:
  bpy.context.scene.frame_set(f);ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());co=np.array([v.co[:] for v in ev.data.vertices]);assert np.isfinite(co).all();assert abs(co).max()<1.4,(action.name,f,abs(co).max());bounds.append([co.min(axis=0).tolist(),co.max(axis=0).tolist()])
 report['actions'][action.name]={'sampled_poses':len(frames),'finite_and_bounded':True}
 print('POSE_CHECK',action.name,len(frames),flush=True)
with open('/workspace/sites/xiaqing-motion-lab/dist/assets/jeans-verification.json','w') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print('JEANS_VERIFICATION_PASS',json.dumps(report,ensure_ascii=False),flush=True)
