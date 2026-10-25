import bpy,bmesh,math,json,numpy as np
PATH='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath=PATH+'xiaqing_optimized.blend')
rig=bpy.data.objects['XiaQing_Rig'];scene=bpy.context.scene;meshes=[o for o in bpy.data.objects if o.type=='MESH'];result={'parts':{},'actions':{}}
for o in meshes:
 bm=bmesh.new();bm.from_mesh(o.data);b=sum(e.is_boundary for e in bm.edges);nm=sum(not e.is_manifold for e in bm.edges);nv=sum(not v.is_manifold for v in bm.verts);loose=sum(not v.link_faces for v in bm.verts)
 assert b==0 and nm==0 and loose==0,(o.name,b,nm,loose)
 result['parts'][o.name]={'open_edges':b,'nonmanifold_edges':nm,'nonmanifold_vertices':nv,'loose_vertices':loose,'vertices':len(bm.verts)};bm.free()
 for v in o.data.vertices:
  ws=[g.weight for g in v.groups if g.weight>1e-7];assert len(ws)<=4 and abs(sum(ws)-1)<1e-4,(o.name,v.index,ws)
cloth=bpy.data.objects['XiaQing_Dress'];ids=np.array([e.vertices[:] for e in cloth.data.edges]);rest=np.array([v.co[:] for v in cloth.data.vertices]);lengths=np.linalg.norm(rest[ids[:,0]]-rest[ids[:,1]],axis=1);mask=lengths>.001
for act in bpy.data.actions:
 rig.animation_data.action=act;start,end=map(int,act.frame_range);frames=sorted(set([start,end]+[round(start+(end-start)*i/10) for i in range(11)]));ratios=[]
 for f in frames:
  scene.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
  for o in meshes:
   ev=o.evaluated_get(dg);coords=np.array([v.co[:] for v in ev.data.vertices]);assert np.isfinite(coords).all();assert np.max(np.abs(coords))<1.6,(act.name,f,o.name)
   if o==cloth:
    ls=np.linalg.norm(coords[ids[:,0]]-coords[ids[:,1]],axis=1);ratios.extend((ls[mask]/lengths[mask]).tolist())
 a=np.array(ratios);result['actions'][act.name]={'samples':len(frames),'cloth_edge_stretch_p99':round(float(np.quantile(a,.99)),3),'cloth_edge_stretch_max':round(float(a.max()),3)}
 print('CHECKED_ACTION',act.name,result['actions'][act.name],flush=True)
assert all(not g.name.endswith('UpLeg') or not any(vg.group==g.index and vg.weight>1e-7 for v in cloth.data.vertices for vg in v.groups) for g in cloth.vertex_groups)
with open(PATH+'verification-report.json','w') as f:json.dump(result,f,indent=2)
print('CLOSED_SKINNING_PASS',json.dumps(result),flush=True)
