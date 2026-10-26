"""Merge shoe/lower-shin patch into an already-open R3 scene.
Usage (from main merge script):
  import runpy
  runpy.run_path('/workspace/hero_13/work/vest-outfit/refinement-r3/shoes/apply_patch.py')
Requires Vest_Body with point INT r2_vertex_id, original R2 IDs on retained points.
This script modifies only source-Z<.285 body points/faces and adds two rigid shoes.
It does not save, export, move ground, or modify upper-body points/materials/weights.
"""
import bpy,bmesh,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
rig=bpy.data.objects['Xiaqing_Native_Rig'];body=bpy.data.objects['Vest_Body'];assert body.data.attributes.get('r2_vertex_id'),'Initialize r2_vertex_id BEFORE any R3 topology changes'
npz=np.load(P/'lower_body_patch.npz');source=npz['source_coords'];cut=.202;end=.285
# Import temporary patch donor object plus shoe objects; retain current scene rig.
preexisting=set(bpy.data.objects)
with bpy.data.libraries.load(str(P/'shoes_rebuilt.blend'),link=False) as (fr,to):to.objects=['Vest_Body','Shoe_L','Shoe_R']
donor,shoe_l,shoe_r=to.objects
lookup={int(a.value):i for i,a in enumerate(donor.data.attributes['r2_vertex_id'].data)}
bodyids=np.array([a.value for a in body.data.attributes['r2_vertex_id'].data]);donornames={g.index:g.name for g in donor.vertex_groups}
changed=0
for vert,rid in zip(body.data.vertices,bodyids):
 if rid<0 or rid not in lookup or source[rid,2]>=end:continue
 d=donor.data.vertices[lookup[rid]];vert.co=d.co
 for g in list(vert.groups):body.vertex_groups[g.group].remove([vert.index])
 for g in d.groups:
  name=donornames[g.group];vg=body.vertex_groups.get(name) or body.vertex_groups.new(name=name);vg.add([vert.index],g.weight,'REPLACE')
 changed+=1
# Robust face matching after upper-body edits: classify by untouched source IDs.
remove=[]
for poly in body.data.polygons:
 ids=bodyids[list(poly.vertices)]
 if np.any(ids<0):continue
 q=source[ids]
 if q[:,2].mean()<cut:remove.append(poly.index)
bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in remove],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(body.data);bm.free()
# Imported parent/armature references are replaced with CURRENT native rig.
for shoe in [shoe_l,shoe_r]:
 bpy.context.scene.collection.objects.link(shoe);shoe.parent=rig;shoe.matrix_parent_inverse=rig.matrix_world.inverted()
 for m in shoe.modifiers:
  if m.type=='ARMATURE':m.object=rig
 assert all(x.value==-1 for x in shoe.data.attributes['r2_vertex_id'].data)
# Remove temporary donor and implicit duplicate rig objects loaded as dependencies.
keep={shoe_l,shoe_r}
for obj in list(bpy.data.objects):
 if obj not in preexisting and obj not in keep:bpy.data.objects.remove(obj,do_unlink=True)
# Recompute lower-shin geometry normals while retaining all upper-body custom normals.
if body.data.has_custom_normals:
 oldn=[n.vector[:] for n in body.data.corner_normals]
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.mesh.customdata_custom_splitnormals_clear();body.data.update();newn=[n.vector[:] for n in body.data.corner_normals]
 ids=np.array([a.value for a in body.data.attributes['r2_vertex_id'].data])
 for loop in body.data.loops:
  rid=ids[loop.vertex_index]
  if rid<0 or source[rid,2]>=end:newn[loop.index]=oldn[loop.index]
 body.data.normals_split_custom_set(newn)
body.data.update();print('SHOE PATCH applied:',changed,'lower shin vertices;',len(remove),'old foot/shoe faces removed;',shoe_l.name,shoe_r.name)
