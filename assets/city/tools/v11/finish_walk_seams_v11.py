"""Close centimetre terrain-cut seams along existing alleys and new rear accesses."""
import bpy,sys,json,math,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--model-dir',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--baseline',type=Path,default=ROOT/'recovery/huizhou_city_v10');ap.add_argument('--deps',type=Path,default=ROOT/'blender_deps');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
sys.path.insert(0,str(args.deps.resolve()));sys.path.insert(0,str(args.baseline.resolve()/'tools'))
import shapely
from shapely.geometry import Polygon,LineString,Point
from city_surface_sampling import HeightField
OUT=args.model_dir.resolve();p=json.loads((OUT/'city_plan.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(OUT/'huizhou_road_network.blend'));bpy.context.view_layer.update();sc=bpy.context.scene
for ob in list(sc.objects):
    if ob.name.startswith(('Rear_Edge_Stitch_','Rear_Edge_Closure_')):bpy.data.objects.remove(ob,do_unlink=True)
terrain=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);parent=bpy.data.objects['10_PEDESTRIAN_NETWORK'];atlas=bpy.data.materials['Road_Modular_Original_Atlas'];concrete=bpy.data.materials['Bridge_Concrete'];count=0
def make(name,v,f,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(v,[],f);data.materials.append(mat);data.update();ob=bpy.data.objects.new(name,data);sc.collection.objects.link(ob);ob.parent=parent;ob['surface_type']='backlane_seam_stitch'
    if mat==atlas:
        layer=data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            for i in poly.loop_indices:
                co=data.vertices[data.loops[i].vertex_index].co;layer.data[i].uv=(.216+.055*((co.x/3)%1),.5989+.1777*((co.y/16.9048)%1))
for name,poly in [(a['name'],LineString(a['points']).buffer(a['width']/2,cap_style=2)) for a in p['pedestrian_alleys']]+[(r['name']+'_Entry_Walk',Polygon(r['polygon'])) for r in p['rear_rows']]:
    old=bpy.data.objects.get(name)
    if old is None:raise RuntimeError(name)
    hf=HeightField([old]);band=shapely.segmentize(poly.buffer(.045,join_style=2).difference(poly.buffer(-.003,join_style=2)),1.8);v=[];f=[]
    def height(xy):
        q=poly.boundary.interpolate(poly.boundary.project(Point(xy)));h=hf.height(q.coords[0],.002)
        if h is None:
            q=poly.buffer(-.001).boundary.interpolate(poly.buffer(-.001).boundary.project(Point(xy)));h=hf.height(q.coords[0],.003)
        if h is None:raise RuntimeError(('cannot sample stitch border',name,list(xy)))
        return h+.001
    for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(band)):
        xy=np.array(tri.exterior.coords)[:3];a=xy[1]-xy[0];b=xy[2]-xy[0]
        if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
        k=len(v);v.extend([[*q,height(q)] for q in xy]);f.append([k,k+1,k+2])
    make('Rear_Edge_Stitch_'+name,v,f,atlas)
    v=[];f=[];ring=shapely.segmentize(poly.buffer(.045,join_style=2),1.8).exterior
    for a,b in zip(ring.coords[:-1],ring.coords[1:]):
        za=height(a);zb=height(b);sa=terrain.height(a);sb=terrain.height(b);ba=min(za-.18,(sa if sa is not None else za)-.12);bb=min(zb-.18,(sb if sb is not None else zb)-.12);k=len(v);v.extend([[*a,ba],[*b,bb],[*b,zb],[*a,za]]);f.extend([[k,k+1,k+2],[k,k+2,k+3]])
    make('Rear_Edge_Closure_'+name,v,f,concrete);count+=1
r=json.loads((OUT/'compact_build_report.json').read_text());r['closed_walkway_edge_seams']=count;(OUT/'compact_build_report.json').write_text(json.dumps(r,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain their textures.')
print('V11_WALK_SEAMS_CLOSED',count,flush=True)
