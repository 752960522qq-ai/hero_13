exec(open('/workspace/sites/xiaqing-motion-lab/tools/validate_jeans_glb.py').read())
from collections import Counter
for mesh in j['meshes']:
 keys={};edge_counts=Counter()
 for p in mesh['primitives']:
  positions=arr(p['attributes']['POSITION']);mapping=[]
  for v in positions:mapping.append(keys.setdefault(tuple(v.tolist()),len(keys)))
  for triangle in arr(p['indices']).reshape(-1,3):
   a,b,c=[mapping[i] for i in triangle]
   if len({a,b,c})<3:continue
   for e in [(a,b),(b,c),(c,a)]:edge_counts[tuple(sorted(e))]+=1
 open_edges=sum(n==1 for n in edge_counts.values());print('EXPORTED_OPEN_EDGES',open_edges)
 assert open_edges==0,(mesh['name'],open_edges)
