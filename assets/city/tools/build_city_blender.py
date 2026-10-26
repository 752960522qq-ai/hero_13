"""Build the city in Blender 4.5, using the supplied Road Modular mesh/UVs.

blender -b --factory-startup --python build_city_blender.py -- \
  --plan generated --roads sources/road_modular.glb --out output
"""
import argparse, collections, json, math, os, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--plan',type=Path,required=True)
parser.add_argument('--roads',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--render',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.out.mkdir(parents=True,exist_ok=True)
plan=json.loads((args.plan/'city_plan.json').read_text())
optimized=plan.get('schema')=='hero13.city.blockout.v2'

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.roads.resolve()))
bpy.context.view_layer.update()

def source_name(o):
    a=o
    while a:
        if any(s in a.name for s in ['Road_33_69','Double road_36_7']):return a.name
        a=a.parent
    return ''

def template(obj):
    obj.data.calc_loop_triangles()
    co=np.array([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
    mi=co.min(axis=0);ma=co.max(axis=0);co[:,0]-=(mi[0]+ma[0])/2;co[:,1]=(co[:,1]-mi[1])/(ma[1]-mi[1]);co[:,2]-=.04324
    uv=obj.data.uv_layers.active.data
    vertices=[];tex=[];faces=[];lookup={}
    for tri in obj.data.loop_triangles:
        f=[]
        for li,vi in zip(tri.loops,tri.vertices):
            u=tuple(uv[li].uv);p=tuple(co[vi]);key=tuple(round(x,6) for x in p+u)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(p);tex.append(u)
            f.append(lookup[key])
        faces.append(f)
    return {'vertices':np.array(vertices),'uv':np.array(tex),'faces':np.array(faces),'width':ma[0]-mi[0],'material':obj.data.materials[0]}

templates={}
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH':continue
    name=source_name(obj)
    if 'Road_33_69' in name:templates['local']=template(obj)
    if 'Double road_36_7' in name:templates['arterial']=template(obj)
assert set(templates)=={'local','arterial'},'Input road kit lacks required straight modules'
roadmat=templates['local']['material'];roadmat.name='Road_Modular_Original_Atlas'
bsdf=next(n for n in roadmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.9
roadmat['source_author']='mortalityrexotable';roadmat['source_license']='CC-BY-4.0'
roadmat['source_url']=plan['sources']['road']['url']
for mat in {t['material'] for t in templates.values()}:
    mat.use_fake_user=True
    for nd in mat.node_tree.nodes:
        if nd.type=='TEX_IMAGE' and nd.image:
            im=nd.image
            if im.size[0]>2:
                im.filepath_raw=str((args.out/'road_atlas.jpg').resolve());im.file_format='JPEG';im.save();im.pack()
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)

SC=bpy.context.scene
SC.unit_settings.system='METRIC';SC.unit_settings.scale_length=1
SC.world.use_nodes=True;SC.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.18,.24,1);SC.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65

def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);SC.collection.objects.link(o);o.parent=parent;o.empty_display_size=50;return o
ROOT=empty('Huizhou_City_4000m_Road_Blockout')
ROOT['description']='Three-island city blockout. Roads use supplied Road Modular mesh and UV atlas; all buildings are replaceable boxes.'
ROOT['units']='metres';ROOT['north']='-Z in exported GLB';ROOT['map_extent_m']=4000
ROOT['source_road_author']='mortalityrexotable';ROOT['source_road_license']='CC-BY-4.0';ROOT['source_road_url']=plan['sources']['road']['url']
ROOT['road_length_m']=round(plan['stats']['road_length_m'],2);ROOT['road_network_components']=1;ROOT['maximum_centerline_grade']=plan['stats']['maximum_road_grade']
GROUPS={name:empty(name,ROOT) for name in ['01_TERRAIN','02_WATER','03_ROAD_NETWORK','04_BRIDGE_STRUCTURES','05_BUILDING_PLACEHOLDERS','06_SIDEWALKS']}
if optimized:
    ROOT['sidewalk_source']='Road Modular / Sidewalk 2_1_75: original mesh top, height and UVs'
    ROOT['sidewalk_width_m']=plan['stats']['sidewalk_width_m']
    ROOT['road_repairs']='Reconnected street ends, merged small junction fragments, faired approaches, continuous road/sidewalk/terrain footprints'
REGIONS={reg:empty(reg,GROUPS['05_BUILDING_PLACEHOLDERS']) for reg in ['MAIN','WEST','EAST']}

def material(name,color,rough=.9,metallic=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metallic
    return m
ASPHALT=material('Junction_Asphalt',(.049,.053,.055))
SIDEWALK=material('Junction_Pavement',(.39,.38,.34))
CONCRETE=material('Bridge_Concrete',(.38,.41,.41))
RAIL=material('Bridge_Parapet',(.65,.69,.67),.65)
SAND=material('Coastal_Shelf',(.39,.36,.25))
SHALLOWS=material('Shallow_Coastal_Water',(.021,.16,.18),.5)
SEA=material('Sea',(.012,.065,.105),.34,.18)
LAKE=material('Lake_Water',(.025,.15,.17),.42,.05)

def mesh(name,verts,faces,mats,uv=None,parent=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    if uv is not None:
        layer=data.uv_layers.new(name='UVMap')
        ids=np.empty(len(data.loops),np.int32);data.loops.foreach_get('vertex_index',ids)
        layer.data.foreach_set('uv',np.asarray(uv,dtype=np.float32)[ids].ravel())
    for mat in mats:data.materials.append(mat)
    obj=bpy.data.objects.new(name,data);SC.collection.objects.link(obj);obj.parent=parent or ROOT
    return obj

buffers={}
def add_to_buffer(name,verts,faces,uv,mat,parent):
    buf=buffers.setdefault(name,{'vertices':[],'faces':[],'uv':[],'mat':mat,'parent':parent})
    off=len(buf['vertices']);buf['vertices'].extend(np.asarray(verts).tolist());buf['faces'].extend((np.asarray(faces)+off).tolist());buf['uv'].extend(np.asarray(uv).tolist())

def frame(edge,dist):
    p=np.array(edge['points']);ds=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
    dist=np.clip(np.asarray(dist),0,ds[-1]);pos=np.stack([np.interp(dist,ds,p[:,i]) for i in range(3)],axis=-1)
    tangent=np.gradient(p[:,:2],ds,axis=0);tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-9)
    t=np.stack([np.interp(dist,ds,tangent[:,i]) for i in range(2)],axis=-1);t/=np.maximum(np.linalg.norm(t,axis=-1,keepdims=True),1e-9)
    norm=np.stack([-t[...,1],t[...,0]],axis=-1)
    return pos,t,norm

edge_ranges={}
continuous_v=[];continuous_f=[]
for ei,edge in enumerate(plan['edges']):
    a=plan['nodes'][edge['a']];b=plan['nodes'][edge['b']];L=edge['length']
    start=min(a['radius'],L*.49);stop=L-min(b['radius'],L*.49)
    edge_ranges[ei]=(start,stop)
    if optimized:
        edge_ranges[ei]=tuple(edge['range'])
        continue
    if stop-start<.25:continue
    typ='arterial' if edge['width']>=20 else 'local';tmp=templates[typ];v=tmp['vertices']
    count=max(1,int(math.ceil((stop-start)/8)))
    bounds=np.linspace(start,stop,count+1)
    dense=np.linspace(start,stop,max(2,int(math.ceil((stop-start)/3))+1));centers,_,normal=frame(edge,dense);baseoff=len(continuous_v)
    for c,n in zip(centers,normal):
        for side in [-1,1]:continuous_v.append([c[0]+n[0]*side*edge['width']/2,c[1]+n[1]*side*edge['width']/2,c[2]-.012])
    for k in range(len(centers)-1):i=baseoff+k*2;continuous_f.append([i,i+2,i+3,i+1])
    for s,e in zip(bounds[:-1],bounds[1:]):
        ss=s+v[:,1]*(e-s);pos,_,n=frame(edge,ss)
        xx=v[:,0]*(edge['width']/tmp['width']);co=pos.copy();co[:,:2]+=n*xx[:,None];co[:,2]+=v[:,2]
        add_to_buffer(edge['name'],co,tmp['faces'],tmp['uv'],roadmat,GROUPS['03_ROAD_NETWORK'])
    if not edge['bridge']:
        distances=np.linspace(start,stop,max(2,int(math.ceil((stop-start)/6))+1));pos,_,normal=frame(edge,distances)
        bed_v=[];bed_f=[]
        for c,n in zip(pos,normal):
            for offset,zoff in [(-edge['width']/2-1.2,-.065),(edge['width']/2+1.2,-.065),(-edge['width']/2-1.2,-.9),(edge['width']/2+1.2,-.9)]:
                bed_v.append([c[0]+n[0]*offset,c[1]+n[1]*offset,c[2]+zoff])
        for k in range(len(pos)-1):
            i=k*4;j=(k+1)*4;bed_f.extend([[i,i+1,j+1,j],[i,j,j+2,i+2],[i+1,i+3,j+3,j+1],[i+2,j+2,j+3,i+3]])
        mesh(edge['name']+'_Road_Foundation_'+str(ei),bed_v,bed_f,[CONCRETE],parent=GROUPS['01_TERRAIN'])
for name,buf in buffers.items():
    obj=mesh(name,buf['vertices'],buf['faces'],[buf['mat']],buf['uv'],buf['parent']);obj['source_mesh']='Road Modular: deformed straight / double-road module';obj['driveable']=True
print('ROAD_SURFACES',len(buffers),sum(len(b['faces']) for b in buffers.values()),flush=True)
buffers.clear()
if not optimized:
    underlay=mesh('Continuous_Pavement_Backstop',continuous_v,continuous_f,[ASPHALT],parent=GROUPS['03_ROAD_NETWORK']);underlay['driveable']=True
else:
    def planned_mesh(filename,name,mat,parent,source=None):
        q=np.load(args.plan/filename)
        if len(q['faces'])==0:return None
        # Preserve UV seams, while sharing identical kit vertices and corner
        # vertices instead of exporting three new vertices for every triangle.
        attributes=np.c_[q['vertices'],q['uv']].astype(np.float32)
        unique,indices=np.unique(attributes,axis=0,return_inverse=True)
        faces=indices[q['faces']]
        obj=mesh(name,unique[:,:3].tolist(),faces.tolist(),[mat],unique[:,3:],parent)
        if source:obj['source_mesh']=source
        return obj
    for reg in ['MAIN','WEST','EAST','BRIDGES']:
        obj=planned_mesh(f'roads_{reg}.npz',reg+'_Road_Modular_Repaired',roadmat,GROUPS['03_ROAD_NETWORK'],'Road_33_69 / Double road_36_7: original cross-section and UVs, longitudinal subdivisions')
        if obj:obj['driveable']=True
        obj=planned_mesh(f'sidewalks_{reg}.npz',reg+'_Sidewalk_Modular_Continuous',roadmat,GROUPS['06_SIDEWALKS'],'Sidewalk 2_1_75: original top mesh and UVs, narrowed to 3m; matching remeshed corners and curbs')
        if obj:obj['walkable']=True;obj['width_m']=3.0
    underlay=planned_mesh('pavement_continuous.npz','Continuous_Pavement_Repaired',ASPHALT,GROUPS['03_ROAD_NETWORK'])
    underlay['driveable']=True
    planned_mesh('sidewalk_underlay.npz','Sidewalk_Continuous_Transition_Base',roadmat,GROUPS['06_SIDEWALKS'],'Sidewalk 2_1_75: original top UVs and height, remeshed continuous transition base 4mm below source tiles')
    planned_mesh('bridge_foundation.npz','Continuous_Bridge_Decks_And_Water_Junction',CONCRETE,GROUPS['04_BRIDGE_STRUCTURES'])

# Junctions replace through-running road stripes and closed-off sidewalk edges.
jbuf=collections.defaultdict(lambda:{'v':[],'f':[],'mi':[]})
jbed=collections.defaultdict(lambda:{'v':[],'f':[]})
for junction in plan['junctions']:
    buf=jbuf[junction['region']]
    for patch in junction['patches']:
        height_offset=.144 if patch['material']=='sidewalk' else 0
        heights=patch.get('z',[junction['z']]*3)
        verts=[[p[0],p[1],z+height_offset] for p,z in zip(patch['xy'],heights)]
        cross=np.cross(np.array(verts[1])-verts[0],np.array(verts[2])-verts[0])
        if cross[2]<0:verts=verts[::-1]
        off=len(buf['v']);buf['v'].extend(verts);buf['f'].append([off,off+1,off+2]);buf['mi'].append(1 if patch['material']=='sidewalk' else 0)
        bed=jbed[junction['region']];joff=len(bed['v']);bed['v'].extend(verts);bed['v'].extend([[p[0],p[1],p[2]-1] for p in verts]);bed['f'].extend([[joff+3,joff+5,joff+4]]+[[joff+i,joff+(i+1)%3,joff+(i+1)%3+3,joff+i+3] for i in range(3)])
for reg,b in jbuf.items():
    o=mesh(f'{reg}_Junction_Aprons',b['v'],b['f'],[ASPHALT,SIDEWALK],parent=GROUPS['03_ROAD_NETWORK'])
    o.data.polygons.foreach_set('material_index',np.array(b['mi'],np.int32));o['driveable']=True
for reg,b in jbed.items():mesh(reg+'_Junction_Foundations',b['v'],b['f'],[CONCRETE],parent=GROUPS['01_TERRAIN'])

# Shore-conforming terrain. Exportable vertex colours keep the file self-contained.
terrain_max=0
for reg in ['MAIN','WEST','EAST']:
    q=np.load(args.plan/f'terrain_{reg}.npz');v=q['vertices'];f=q['faces'].copy();terrain_max=max(terrain_max,float(v[:,2].max()))
    # SciPy triangulations are CCW; GEOS constrained fragments are CW. Mixing
    # them made the old clipped road shoulders shade as black triangles.
    p=v[f,:2];cross=(p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]);f[cross<0]=f[cross<0][:,::-1]
    mat=material(f'{reg}_Terrain',(.22,.31,.15))
    bs=mat.node_tree.nodes.get('Principled BSDF');col=mat.node_tree.nodes.new('ShaderNodeVertexColor');col.layer_name='Color';mat.node_tree.links.new(col.outputs['Color'],bs.inputs['Base Color'])
    o=mesh(f'{reg}_Sculpted_Terrain',v.tolist(),f.tolist(),[mat],parent=GROUPS['01_TERRAIN'])
    colors=np.zeros((len(v),4),np.float32);noise=.025*np.sin(v[:,0]/39)*np.sin(v[:,1]/53)
    colors[:,:3]=np.array([.19,.28,.115])[None,:]+noise[:,None]
    if reg=='EAST':colors[:,:3]=np.array([.23,.28,.145])[None,:]+noise[:,None]
    weight=np.clip((v[:,2]-50)/130,0,1);colors[:,:3]=colors[:,:3]*(1-weight[:,None]) + np.array([.24,.29,.14])*weight[:,None]
    shore=np.clip((6-v[:,2])/4,0,1);colors[:,:3]=colors[:,:3]*(1-shore[:,None])+np.array([.49,.44,.29])*shore[:,None]
    colors[:,3]=1;c=o.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT');c.data.foreach_set('color',colors.ravel())
    for poly in o.data.polygons:poly.use_smooth=True
    coast=q['coast'];n=len(coast);vv=[];ff=[]
    center=coast.mean(axis=0)
    for p in coast:
        direction=p-center;direction/=np.linalg.norm(direction)
        vv.extend([[*p,2.3],[*(p+direction*14),-.6],[*(p+direction*34),-2.5]])
    for i in range(n-1):
        for k in [0,1]:ff.append([i*3+k,(i+1)*3+k,(i+1)*3+k+1,i*3+k+1])
    shelf=mesh(f'{reg}_Intertidal_Shelf',vv,ff,[SAND],parent=GROUPS['01_TERRAIN'])

mesh('Sea_4000m',[[-2000,-2000,0],[2000,-2000,0],[2000,2000,0],[-2000,2000,0]],[[0,1,2,3]],[SEA],parent=GROUPS['02_WATER'])
lv=[[p[0],p[1],plan['lake_level']] for p in plan['lake'][:-1]]
# The plan ring orientation is normalised here for a visible upper surface.
if sum(lv[i][0]*lv[(i+1)%len(lv)][1]-lv[(i+1)%len(lv)][0]*lv[i][1] for i in range(len(lv)))<0:lv=lv[::-1]
lakeobj=mesh('West_Island_Lake_Level_22m',lv,[list(range(len(lv)))],[LAKE],parent=GROUPS['02_WATER']);lakeobj['water_level_m']=22

CUBEV=[[-.5,-.5,-.5],[-.5,-.5,.5],[-.5,.5,-.5],[-.5,.5,.5],[.5,-.5,-.5],[.5,-.5,.5],[.5,.5,-.5],[.5,.5,.5]]
CUBEF=[[0,4,6,2],[1,3,7,5],[0,1,5,4],[2,6,7,3],[0,2,3,1],[4,5,7,6]]
cube_data={}
def cube(name,location,scale,mat,parent,angle=0):
    if mat.name not in cube_data:
        d=bpy.data.meshes.new('Shared_Box_'+mat.name);d.from_pydata(CUBEV,[],CUBEF);d.materials.append(mat);d.update();cube_data[mat.name]=d
    obj=bpy.data.objects.new(name,cube_data[mat.name]);SC.collection.objects.link(obj);obj.parent=parent;obj.location=location;obj.scale=scale;obj.rotation_euler[2]=angle
    return obj

ZONE_COLORS={'CBD':(.45,.55,.61),'CIVIC':(.62,.63,.59),'UNIVERSITY':(.69,.64,.52),'OLDTOWN':(.58,.51,.42),'CULTURE':(.64,.64,.58),'RESIDENTIAL':(.61,.62,.58),'VILLAGE':(.65,.57,.43),'RESORT':(.64,.65,.54),'FRINGE':(.57,.56,.49),'INDUSTRIAL':(.39,.45,.47),'LANDMARK':(.63,.72,.75),'DOCK':(.35,.37,.34)}
zone_mats={z:material(z+'_Placeholder_Box',c) for z,c in ZONE_COLORS.items()}
for b in plan['buildings']:
    x,y=b['center'];sx,sy,h=b['size'];o=cube(b['name'],(x,y,b['base']+h/2),(sx,sy,h),zone_mats[b['zone']],REGIONS[b['region']]);o['is_placeholder']=True;o['district']=b['zone'];o['replaceable_id']=b['name']
for b in plan['props']:
    x,y=b['center'];sx,sy,h=b['size'];o=cube(b['name'],(x,y,b['base']+h/2),(sx,sy,h),zone_mats[b['zone']],REGIONS['EAST']);o['is_placeholder']=True

# Bridge decks, piers and parapets are also simple replaceable box elements.
bridge_piers=0
for ei,edge in enumerate(plan['edges']):
    if not edge['bridge']:continue
    start,stop=edge_ranges[ei];length=stop-start
    if length<1:continue
    n=max(1,int(math.ceil(length/14)));dd=np.linspace(start,stop,n+1);p,t,norm=frame(edge,dd)
    bg=GROUPS['04_BRIDGE_STRUCTURES']
    for k in range(len(p)-1):
        mid=(p[k]+p[k+1])/2;d=p[k+1]-p[k];angle=math.atan2(d[1],d[0]);l=float(np.linalg.norm(d[:2]));width=edge['width']
        # Vertical box rotation is applied only where the elevated bridge needs it.
        tilt=-math.atan2(d[2],max(l,.01))
        if not optimized:
            beam=cube(f'{edge["name"]}_Deck_{ei}_{k}',(mid[0],mid[1],mid[2]-.78),(l+.1,width,1.35),CONCRETE,bg,angle)
            beam.rotation_euler[1]=tilt
        for side in [-1,1]:
            nvec=(norm[k]+norm[k+1])/2;loc=mid.copy();loc[:2]+=nvec*side*(width/2-.38);loc[2]+=.68
            rail=cube(f'{edge["name"]}_Parapet_{ei}_{k}_{side}',loc,(l+.1,.35,.8),RAIL,bg,angle);rail.rotation_euler[1]=tilt
    for d in np.arange(start+22,stop-8,56):
        pos,_,nvec=frame(edge,np.array([d]));pos=pos[0]
        # No pillars in the live road surface; all are beneath its deck.
        height=pos[2]-.95+4
        if height>8:
            for side in [-1,1]:
                loc=pos.copy();loc[:2]+=nvec[0]*side*6;loc[2]=-4+height/2
                cube(f'{edge["name"]}_Pier_{bridge_piers:03}',loc,(2.4,3.1,height),CONCRETE,bg);bridge_piers+=1

ROOT['terrain_max_height_m']=round(terrain_max,2)
ROOT['placeholder_building_count']=len(plan['buildings'])
ROOT['bridge_pier_count']=bridge_piers

# Verify all geometry before native save and export.
for obj in SC.objects:
    if obj.type=='MESH':
        assert not any(not math.isfinite(c) for v in obj.data.vertices for c in v.co),obj.name
        obj.data.validate(verbose=False)
        obj.data.update()
SC.render.engine='CYCLES';SC.cycles.samples=24;SC.cycles.use_denoising=True
SC.render.resolution_percentage=100;SC.render.image_settings.file_format='PNG'
SC.view_settings.view_transform='AgX'
SC.render.film_transparent=False
sun=bpy.data.lights.new('Presentation_Sun','SUN');lo=bpy.data.objects.new('Presentation_Sun',sun);SC.collection.objects.link(lo);sun.energy=3.2;sun.angle=.2;lo.rotation_euler=(math.radians(28),math.radians(-23),math.radians(-32))
camdata=bpy.data.cameras.new('Presentation_Camera');cam=bpy.data.objects.new('Presentation_Camera',camdata);SC.collection.objects.link(cam);SC.camera=cam;camdata.clip_end=30000
def camera(location,target,ortho=None,lens=40):
    cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO' if ortho else 'PERSP';camdata.ortho_scale=ortho or 100;camdata.lens=lens
camera((3700,-4800,5400),(0,30,25),5150)
SC.render.resolution_x=1800;SC.render.resolution_y=1600
bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'huizhou_road_network.blend').resolve()),compress=True)
kwargs={'filepath':str((args.out/'huizhou_road_network.glb').resolve()),'export_format':'GLB','export_yup':True,'export_extras':True,'export_animations':False,'export_cameras':False,'export_lights':False,'export_materials':'EXPORT','export_image_format':'JPEG','export_copyright':'Road Modular by mortalityrexotable, CC BY 4.0; road meshes deformed and assembled into a new city blockout. '+plan['sources']['road']['url']}
available=bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
if 'export_image_quality' in available:kwargs['export_image_quality']=90
bpy.ops.export_scene.gltf(**kwargs)
print('CITY_EXPORTED',json.dumps({'objects':len(SC.objects),'mesh_objects':sum(o.type=='MESH' for o in SC.objects),'road_triangles':sum(len(o.data.polygons) for o in SC.objects if o.type=='MESH' and o.parent==GROUPS['03_ROAD_NETWORK']),'terrain_peak_m':terrain_max,'bridge_piers':bridge_piers,'bytes':(args.out/'huizhou_road_network.glb').stat().st_size}),flush=True)
if args.render:
    for name,loc,target,ortho,res in [
        ('city_aerial',(3700,-4800,5400),(0,30,25),5150,(1800,1600)),
        ('city_top',(0,0,7000),(0,0,0),4010,(1800,1800)),
        ('city_hills',(-1120,290,330),(-960,1030,58),None,(1700,1100)),
        ('city_bridges',(550,-1230,280),(45,-500,26),None,(1700,1100))]:
        camera(loc,target,ortho);SC.render.resolution_x,SC.render.resolution_y=res;SC.render.filepath=str((args.out/(name+'.png')).resolve());bpy.ops.render.render(write_still=True)
print('CITY_BUILD_COMPLETE',flush=True)
