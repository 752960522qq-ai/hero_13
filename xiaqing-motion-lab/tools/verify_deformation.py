import bpy,math,json
bpy.ops.wm.open_mainfile(filepath='/workspace/sites/xiaqing-motion-lab/dist/assets/xiaqing_optimized.blend')
rig=bpy.data.objects['XiaQing_Rig'];meshes=[o for o in bpy.data.objects if o.type=='MESH'];report={}
for action in bpy.data.actions:
 rig.animation_data.action=action;start,end=map(int,action.frame_range);maximum=0
 for f in sorted(set([start,end]+[round(start+(end-start)*i/10) for i in range(11)])):
  bpy.context.scene.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
  for o in meshes:
   ev=o.evaluated_get(dg)
   for v in ev.data.vertices:
    assert all(math.isfinite(x) for x in v.co)
    assert v.co.length<2,(action.name,f,o.name,v.index)
   maximum=max(maximum,max(v.co.length for v in ev.data.vertices))
 report[action.name]={'sampled_poses':11,'maximum_radius':round(maximum,4),'finite_and_bounded':True}
print('DEFORMATION_PASS',json.dumps(report),flush=True)
