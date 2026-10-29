import bpy,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(P/'double_stars_bound.blend'));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');count={b.name:0 for b in t.data.bones};bad=0;zeros=0
for o in bpy.data.objects:
 if o.type!='MESH':continue
 names={g.index:g.name for g in o.vertex_groups}
 for v in o.data.vertices:
  total=sum(g.weight for g in v.groups);bad+=abs(total-1)>1e-5;zeros+=total<1e-8
  for g in v.groups:
   if g.weight>.01:count[names[g.group]]+=1
hands={n:k for n,k in count.items() if any(x in n for x in ['thumb_','index_','middle_','ring_','pinky_'])}
(P/'weight_validation.json').write_text(json.dumps({'unnormalized_vertices':bad,'unweighted_vertices':zeros,'finger_vertices_over_1_percent':hands,'weighted_bones':{n:k for n,k in count.items()if k}},indent=2));print('WEIGHTS',bad,zeros,hands,flush=True)
