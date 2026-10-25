"""Refit trouser cuffs to native calf sections in Blender, retaining UVs and rig."""
import bpy, math, json, struct
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'qa/ankle-alignment';OUT.mkdir(exist_ok=True)
ASSET=ROOT/'dist/assets/wardrobe/shirt_trouser_rigged.glb'
original_bytes=ASSET.read_bytes()

def sections(vertices, faces, height, side):
    triangles=vertices[faces]
    triangles=triangles[(triangles[:,:,0].mean(1)*side>0)&(triangles[:,:,2].min(1)<height)&(triangles[:,:,2].max(1)>height)]
    segments=[]
    for tri in triangles:
        hits=[]
        for a,b in [(0,1),(1,2),(2,0)]:
            va,vb=tri[a],tri[b]
            if (va[2]-height)*(vb[2]-height)<0:
                hits.append((va+(vb-va)*((height-va[2])/(vb[2]-va[2])) )[:2])
        if len(hits)==2:segments.append(hits)
    return np.array(segments)

def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]

def mesh_arrays(obj):
    obj.data.calc_loop_triangles()
    return np.array([tuple(obj.matrix_world@v.co) for v in obj.data.vertices]),np.array([tuple(t.vertices) for t in obj.data.loop_triangles])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'dist/assets/xiaqing_native_animated.glb'))
body=bpy.data.objects['pl2020_Skin_Mat'];bv,bf=mesh_arrays(body)
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ASSET))
bpy.context.view_layer.update()
report={'clearanceMeters':.004,'fullFitBelowMeters':.27,'unchangedAboveMeters':.34,'meshes':[]}
for side,sign in [('l',1),('r',-1)]:
    obj=bpy.data.objects['Suit_calf_'+side];v,f=mesh_arrays(obj);low=v[:,2].min()
    heights=np.linspace(low+.00001,.34,100);centers=[];bodyCenters=[];radii=[]
    angles=np.linspace(-math.pi,math.pi,129);directions=np.stack([np.cos(angles),np.sin(angles)],1)
    for h in heights:
        native=sections(bv,bf,h,sign);cloth=sections(v,f,h,sign)
        points=native.reshape(-1,2);center=(points.min(0)+points.max(0))*.5;bodyCenters.append(center)
        points=cloth.reshape(-1,2);centers.append((points.min(0)+points.max(0))*.5)
        a=native[:,0]-center;edge=native[:,1]-native[:,0];rs=[]
        for d in directions:
            den=cross(d,edge);valid=np.abs(den)>1e-10;distance=np.zeros(len(edge));u=np.zeros(len(edge))
            distance[valid]=cross(a[valid],edge[valid])/den[valid];u[valid]=cross(a[valid],d)/den[valid]
            hit=valid&(u>=-1e-6)&(u<=1+1e-6)&(distance>=0)
            if not hit.any():raise RuntimeError('Open calf cross-section')
            rs.append(float(distance[hit].max()))
        radii.append(rs)
    centers=np.array(centers);bodyCenters=np.array(bodyCenters);radii=np.array(radii)
    result=v.copy();changed=0
    for i,point in enumerate(v):
        h=point[2]
        if h>=.34:continue
        old=np.array([np.interp(h,heights,centers[:,axis]) for axis in range(2)])
        new=np.array([np.interp(h,heights,bodyCenters[:,axis]) for axis in range(2)])
        delta=point[:2]-old;radius=np.linalg.norm(delta);angle=math.atan2(delta[1],delta[0])
        nativeRadius=np.interp(h,heights,[np.interp(angle,angles,row) for row in radii])
        target=new+delta/max(radius,1e-10)*max(radius,nativeRadius+.004)
        t=np.clip((h-.27)/(.34-.27),0,1);fade=1-t*t*(3-2*t)
        result[i,:2]=point[:2]+fade*(target-point[:2]);changed+=1
    inverse=obj.matrix_world.inverted()
    from mathutils import Vector
    for vert,pos in zip(obj.data.vertices,result):vert.co=inverse@Vector(pos)
    # Discard stale custom normals after the local surface deformation.
    bpy.context.view_layer.objects.active=obj
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    obj.data.update()
    report['meshes'].append({'name':obj.name,'verticesAdjusted':changed,'maxDisplacementMeters':float(np.linalg.norm(result-v,axis=1).max()),'uvLayers':len(obj.data.uv_layers),'vertexGroups':len(obj.vertex_groups)})
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'trouser_ankles_corrected.blend'),compress=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(OUT/'blender-export.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_extras=True)
# Transplant only the two calf position/normal buffers into the original GLB.
# This avoids Blender round-trip changes to unrelated meshes, skins and textures.
def unpack(raw):
    length=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+length]),bytearray(raw[28+length:])
def array(document,binary,index):
    a=document['accessors'][index];view=document['bufferViews'][a['bufferView']]
    dtype={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]
    count={'VEC2':2,'VEC3':3,'VEC4':4,'SCALAR':1}[a['type']]
    return np.ndarray((a['count'],count),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+a.get('byteOffset',0),strides=(view.get('byteStride',np.dtype(dtype).itemsize*count),np.dtype(dtype).itemsize))
def primitive(document,name):
    node=next(n for n in document['nodes'] if n.get('name')==name)
    return document['meshes'][node['mesh']]['primitives'][0]
original,binary=unpack(original_bytes);exported,export_binary=unpack((OUT/'blender-export.glb').read_bytes())
for name in ['Suit_calf_l','Suit_calf_r']:
    a=primitive(original,name);b=primitive(exported,name)
    for key in ['TEXCOORD_0','JOINTS_0']:
        assert np.array_equal(array(original,binary,a['attributes'][key]),array(exported,export_binary,b['attributes'][key])),key
    assert np.array_equal(array(original,binary,a['indices']),array(exported,export_binary,b['indices']))
    old_pos=array(original,binary,a['attributes']['POSITION']).copy()
    fade=np.clip((old_pos[:,1]-.27)/.07,0,1);fade=1-fade*fade*(3-2*fade)
    for key in ['POSITION','NORMAL']:
        target=array(original,binary,a['attributes'][key]);value=array(exported,export_binary,b['attributes'][key]).copy()
        if key=='NORMAL':
            value=target*(1-fade[:,None])+value*fade[:,None];value/=np.linalg.norm(value,axis=1)[:,None]
        unchanged=fade==0;value[unchanged]=target[unchanged];target[:]=value
        meta=original['accessors'][a['attributes'][key]]
        if 'min' in meta:meta['min']=target.min(0).tolist()
        if 'max' in meta:meta['max']=target.max(0).tolist()
encoded=json.dumps(original,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
binary+=b'\0'*((-len(binary))%4)
ASSET.write_bytes(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)
report['preserved']='Original indices, UVs, weights, joints, inverse bind matrices, textures and all non-calf geometry'
(OUT/'blender-refit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
