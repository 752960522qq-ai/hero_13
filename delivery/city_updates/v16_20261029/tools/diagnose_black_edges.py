import os
import bpy,sys,json,numpy as np,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')));import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
bpy.ops.wm.read_factory_settings(use_empty=True)
for d in [6,7,8]:
 f=next((R/'baseline').glob(f'{d:02d}_*.glb'));bpy.ops.import_scene.gltf(filepath=str(f))
bpy.context.view_layer.update();rows=[];hashes={};duplicates=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 source=o.get('source_object','');m=o.data;m.calc_loop_triangles();M=np.array(o.matrix_world);co=np.array([v.co[:] for v in m.vertices]);co=co@M[:3,:3].T+M[:3,3]
 if 'Retaining' in source:
  # Canonical triangle coordinates ignore face winding and ordering.
  ts=[]
  for t in m.loop_triangles:
   q=np.round(co[list(t.vertices)],4);q=q[np.lexsort(q.T[::-1])];ts.append(q.tobytes())
  h=hashlib.sha256(b''.join(sorted(ts))).hexdigest()
  if h in hashes:duplicates.append([hashes[h],o.name,len(ts)])
  else:hashes[h]=o.name
 if not source.endswith('_Foundation'):continue
 name=source[:-len('_Foundation')];walks=[w for w in bpy.context.scene.objects if w.type=='MESH' and w.get('source_object','').startswith(name+'_') and w.get('surface_type')=='v15_access_walk']
 if not walks:continue
 top=max(co[:,2]);polys=[Polygon(co[list(t.vertices),:2]) for t in m.loop_triangles if np.ptp(co[list(t.vertices),2])<.001 and abs(co[list(t.vertices),2].mean()-top)<.001];F=unary_union(polys);W=[]
 for w in walks:
  w.data.calc_loop_triangles();wm=np.array(w.matrix_world);wc=np.array([v.co[:] for v in w.data.vertices]);wc=wc@wm[:3,:3].T+wm[:3,3]
  W.extend(Polygon(wc[list(t.vertices),:2]) for t in w.data.loop_triangles if np.ptp(wc[list(t.vertices),2])<.001 and abs(wc[list(t.vertices),2].mean()-top)<.001)
 area=F.intersection(unary_union(W)).area
 if area>.01:rows.append({'foundation':o.name,'walk_overlap_m2':area,'height_m':float(top)})
(R/'black_edge_diagnosis.json').write_text(json.dumps({'coplanar_foundations':rows,'coplanar_area_m2':sum(r['walk_overlap_m2'] for r in rows),'duplicate_retaining_meshes':duplicates},indent=2));print('DIAGNOSIS',len(rows),sum(r['walk_overlap_m2'] for r in rows),duplicates,flush=True)
