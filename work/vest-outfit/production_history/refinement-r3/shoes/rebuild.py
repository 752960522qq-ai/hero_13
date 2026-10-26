"""Restore source high heels with a single uniform similarity transform per side.
Foot skin is welded to the shoes in the atlas source; keep complete source foot+shoe
and blend only lower shin coordinates/weights into the R2 body above the ankle strap.
"""
import bpy,bmesh,numpy as np,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;BASE=P.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(P/'source_processed.blend'));source=bpy.context.scene.objects.get('meshes[0]') or next(o for o in bpy.context.scene.objects if o.type=='MESH');srcdata=source.data.copy();srcpos=np.array([v.co[:] for v in srcdata.vertices]);source_faces=[tuple(p.vertices) for p in srcdata.polygons]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'refinement-r2/vest_xiaqing_r2.blend'))
o=bpy.data.objects['Vest_Body'];rig=bpy.data.objects['Xiaqing_Native_Rig'];rig.data.pose_position='REST';rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis.identity()
assert len(srcpos)==len(o.data.vertices)==68198
oldpos=np.array([v.co[:] for v in o.data.vertices]);N=len(oldpos)
# Source and R2 topology retained through earlier deterministic processed import.
assert all(tuple(p.vertices)==source_faces[i] for i,p in enumerate(o.data.polygons))
SCALE=1.7;CUT=.202;BLEND_END=.285
sid=o.data.attributes.get('r2_vertex_id') or o.data.attributes.new('r2_vertex_id','INT','POINT');sid.data.foreach_set('value',np.arange(N,dtype=np.int32))
sourceid=o.data.attributes.get('source_vertex_id') or o.data.attributes.new('source_vertex_id','INT','POINT');sourceid.data.foreach_set('value',np.arange(N,dtype=np.int32))
face_masks={};shoe_vids={};coords=oldpos.copy();report={'method':'source whole-foot plus high-heel rigid restoration; uniform scale only; lower-shin smooth transition','uniform_scale':SCALE,'source_cut_z':CUT,'source_blend_end_z':BLEND_END,'shoes':{}}
for side,sign in [('l',1),('r',-1)]:
 ankle=np.array(rig.matrix_world@rig.data.bones[side+'_leg_ankle'].head_local);srcankle=np.array([sign*.064,.085,.140]);translation=ankle-SCALE*srcankle
 face_masks[side]=np.array([np.mean(srcpos[list(p.vertices)],axis=0)[2]<CUT and np.mean(srcpos[list(p.vertices)],axis=0)[0]*sign>0 for p in o.data.polygons]);shoe_vids[side]=np.unique(np.concatenate([np.array(o.data.polygons[i].vertices) for i in np.where(face_masks[side])[0]]));top=float(srcpos[shoe_vids[side],2].max())
 ids=np.where((srcpos[:,0]*sign>0)&(srcpos[:,2]<BLEND_END))[0];t=np.clip((srcpos[ids,2]-top)/(BLEND_END-top),0,1);t=t*t*(3-2*t);sourcefit=srcpos[ids]*SCALE+translation
 coords[ids]=sourcefit*(1-t[:,None])+oldpos[ids]*t[:,None]
 # Rigid source foot, then smoothly recover original tibia twist weights above cut.
 wi=o.vertex_groups.get(side+'_leg_ankle');assert wi
 for idx,a in zip(ids,1-t):
  if a<1e-8:continue
  row={g.group:g.weight*(1-float(a)) for g in o.data.vertices[int(idx)].groups};row[wi.index]=row.get(wi.index,0)+float(a)
  for g in list(o.data.vertices[int(idx)].groups):o.vertex_groups[g.group].remove([int(idx)])
  topws=sorted(row.items(),key=lambda it:-it[1])[:4];total=sum(w for j,w in topws)
  for j,w in topws:
   if w>1e-9:o.vertex_groups[j].add([int(idx)],w/total,'REPLACE')
 report['shoes'][side]={'source_vertices':int(len(shoe_vids[side])),'source_faces':int(face_masks[side].sum()),'translation':translation.tolist(),'rotation':'identity','source_cut_max_z':top,'ankle_anchor':ankle.tolist()}
for v,p in zip(o.data.vertices,coords):v.co=p
# Shoe objects copy ORIGINAL UV atlas and triangles. Exact source shape for all vertices.
for side,sign in [('l',1),('r',-1)]:
 shoe=o.copy();shoe.data=o.data.copy();shoe.name='Shoe_'+side.upper();bpy.context.scene.collection.objects.link(shoe)
 attr=shoe.data.attributes['r2_vertex_id'];attr.data.foreach_set('value',np.full(N,-1,dtype=np.int32));trans=np.array(report['shoes'][side]['translation'])
 for vertex,point in zip(shoe.data.vertices,srcpos*SCALE+trans):vertex.co=point
 bm=bmesh.new();bm.from_mesh(shoe.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for i,f in enumerate(bm.faces) if not face_masks[side][i]],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(shoe.data);bm.free()
 for group in list(shoe.vertex_groups):shoe.vertex_groups.remove(group)
 shoe.vertex_groups.new(name=side+'_leg_ankle').add(list(range(len(shoe.data.vertices))),1,'REPLACE')
 shoe['source']='vest_source.glb';shoe['uniform_scale']=SCALE;shoe['rigid_ankle_binding']=True;shoe['rest_shape_policy']='All shoe and attached foot vertices use source coordinates * 1.7 + side translation; no RBF, no toe weights.'
 # Original source custom normals need uniform transformation too; re-read source normals for loops by original poly identity.
 # Clear stale R2 normals after replacing geometry, then use geometric smooth normals.
 if shoe.data.has_custom_normals:
  bpy.ops.object.select_all(action='DESELECT');shoe.select_set(True);bpy.context.view_layer.objects.active=shoe;bpy.ops.mesh.customdata_custom_splitnormals_clear()
 shoe.data.update()
 report['shoes'][side]['object']=shoe.name
# Remove original deformed feet and shoes from body, retaining source IDs on remaining verts.
remove=face_masks['l']|face_masks['r'];bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for i,f in enumerate(bm.faces) if remove[i]],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free()
# Lower-shin recomputed normals; leave untouched upper-body custom normals as stored.
if o.data.has_custom_normals:
 oldn=[n.vector[:] for n in o.data.corner_normals];bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.mesh.customdata_custom_splitnormals_clear();o.data.update();newn=[n.vector[:] for n in o.data.corner_normals];ids=np.array([a.value for a in o.data.attributes['r2_vertex_id'].data]);
 for loop in o.data.loops:
  if srcpos[ids[loop.vertex_index],2]>=BLEND_END:newn[loop.index]=oldn[loop.index]
 o.data.normals_split_custom_set(newn)
changed=np.where(np.linalg.norm(coords-oldpos,axis=1)>1e-9)[0]
np.savez(P/'lower_body_patch.npz',r2_vertex_id=changed,coords=coords[changed],removed_face_ids=np.where(remove)[0],shoe_l_source_vertices=shoe_vids['l'],shoe_r_source_vertices=shoe_vids['r'],source_coords=srcpos,uniform_scale=SCALE,l_translation=report['shoes']['l']['translation'],r_translation=report['shoes']['r']['translation'])
report['body_vertices_after']=len(o.data.vertices);report['body_transition_changed_vertices']=len(changed);report['r2_vertex_id_policy']='Body retains original R2 IDs, Shoe_L/R r2_vertex_id=-1; source_vertex_id maps original processed source.'
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'shoes_rebuilt.blend'),compress=True);(P/'rebuild_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
