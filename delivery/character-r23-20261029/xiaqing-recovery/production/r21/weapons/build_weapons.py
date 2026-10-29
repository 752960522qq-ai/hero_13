import bpy,json,os,hashlib
from mathutils import Vector
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=str(P);ASSETS=str(P.parents[2]/'dist/assets')
def reset(fp):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=fp)
def save(fp):
 bpy.ops.export_scene.gltf(filepath=fp,export_format='GLB',export_animations=False,export_yup=True)
# Native QBZ model has -Y barrel, +Z up in Blender. Keep axes and normalize length.
reset(str(P.parent/'inputs/qbz95.glb'))
meshes=[o for o in bpy.data.objects if o.type=='MESH'];vs=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=Vector([min(v[i]for v in vs)for i in range(3)]);hi=Vector([max(v[i]for v in vs)for i in range(3)])
scale=.746/(hi.y-lo.y);grip=Vector((0,.035,.165))
for o in meshes:
 mw=o.matrix_world.copy();o.parent=None;o.matrix_world.identity()
 for v in o.data.vertices:v.co=(mw@v.co-grip)*scale
for o in list(bpy.data.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/qbz95_normalized.blend');save(ASSETS+'/qbz95.glb')
def coords(p):
 v=(Vector(p)-grip)*scale;return [v.x,v.z,-v.y]
manifest={'qbz95':{'name':'95式','label':'95式','url':'./assets/qbz95.glb?v=r21','grip':[0,0,0],'supportGrip':coords((0,-.195,.238)),'supportGripZRange':[.12,.23],'stock':coords((0,.465,.285)),'muzzle':coords((0,-.489,.281)),'visualLength':.746,'coordinateFrame':'glTF/Three.js: +Z barrel-forward, +Y weapon-up; grip at origin','sourceLength':hi.y-lo.y,'normalizationScale':scale}}
# Detach the existing scanned Type56 magazine without modifying body proportions.
reset(ASSETS+'/type56.glb');body=next(o for o in bpy.data.objects if o.type=='MESH');body.name='WeaponBody';mesh=body.data
magfaces=[]
for p in mesh.polygons:
 c=sum((mesh.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
 if c.z<.073 and c.y<-.12 and all(mesh.vertices[i].co.z<.05 or mesh.vertices[i].co.y>-.195 for i in p.vertices):magfaces.append(p.index)
# Keep the largest contiguous patch (using position-keyed edges across UV seams).
face_set=set(magfaces);edge_faces={};adj={i:set() for i in magfaces}
def key(v): return tuple(round(float(x),5) for x in mesh.vertices[v].co)
for i in magfaces:
    verts=list(mesh.polygons[i].vertices)
    for j in range(len(verts)):
        edge=tuple(sorted((key(verts[j]),key(verts[(j+1)%len(verts)]))))
        edge_faces.setdefault(edge,[]).append(i)
for group in edge_faces.values():
    for i in group: adj[i].update(group)
components=[];seen=set()
for i in magfaces:
    if i in seen: continue
    stack=[i];seen.add(i);comp=[]
    while stack:
        j=stack.pop();comp.append(j)
        for k in adj[j]:
            if k not in seen:seen.add(k);stack.append(k)
    components.append(comp)
magfaces=set(max(components,key=len))
print('Magazine candidate components',sorted([len(x) for x in components],reverse=True))
# Duplicate data, then delete inverse face sets in edit mode. This keeps UV/materials/normals.
mag=body.copy();mag.data=body.data.copy();bpy.context.collection.objects.link(mag);mag.name='Magazine'
for o,keep in [(body,False),(mag,True)]:
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 for p in o.data.polygons:p.select=(p.index not in magfaces) if keep else (p.index in magfaces)
 bpy.context.tool_settings.mesh_select_mode=(False,False,True)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='FACE');bpy.ops.object.mode_set(mode='OBJECT')
# Named magazine origin at its seated top center simplifies palm-relative assembly.
origin=Vector((0,-.158,.071));mag.data.transform(__import__('mathutils').Matrix.Translation(-origin));mag.location=origin
mag['role']='detachable magazine';mag['source']='cut from original type56 surface; original UV and materials preserved'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/type56_reload.blend');save(ASSETS+'/type56_reload.glb')
manifest['type56_reload']={'magazineNode':'Magazine','magazineOrigin':[origin.x,origin.z,-origin.y],'facesMagazine':len(mag.data.polygons),'facesBody':len(body.data.polygons),'sourceFaceCount':13974,'url':'./assets/type56_reload.glb?v=r21','nativeVisualLength':.9,'recommendedVisualLength':.874}
open(ROOT+'/weapons_r21.json','w').write(json.dumps(manifest,indent=2));print(json.dumps(manifest))
# Exploded view project for visual verification only, not exported.
mag.location.z-=.15;bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/type56_exploded_preview.blend')
