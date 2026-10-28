"""Close vertical soil faces where rear-house pads and alleys cut into uphill ground."""
import bpy,sys,json,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--model-dir',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--baseline',type=Path,default=ROOT/'recovery/huizhou_city_v10');ap.add_argument('--deps',type=Path,default=ROOT/'blender_deps');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
sys.path.insert(0,str(args.deps.resolve()));sys.path.insert(0,str(args.baseline.resolve()/'tools'))
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from city_surface_sampling import HeightField
OUT=args.model_dir.resolve();p=json.loads((OUT/'city_plan.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(args.baseline.resolve()/'huizhou_road_network.blend'));bpy.context.view_layer.update();soil=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
bpy.ops.wm.open_mainfile(filepath=str(OUT/'huizhou_road_network.blend'));bpy.context.view_layer.update();sc=bpy.context.scene
for ob in list(sc.objects):
    if ob.name.startswith('Rear_Terrain_Cut_Closure_'):bpy.data.objects.remove(ob,do_unlink=True)
names={a['name'] for a in p['pedestrian_alleys']};surfaces=HeightField([o for o in sc.objects if o.type=='MESH' and (o.name in names or o.name.endswith('_Foundation') or o.get('surface_type') in ['sidewalk','backlane_entry_walk','backlane_seam_stitch'])])
cuts=unary_union([Polygon(r['pad_xy']) for r in p['real_buildings'][15:]]+[Polygon(r['polygon']).buffer(.015,join_style=2) for r in p['rear_rows']]+[LineString(a['points']).buffer(a['width']/2+.03,cap_style=2) for a in p['pedestrian_alleys']]);cuts=shapely.orient_polygons(cuts,exterior_cw=False)
v=[];f=[];segments=0;missing=0
def floor_at(q,n,mid=None):
    for d in [.025,.05,.12,.25,.5]:
        z=surfaces.height(np.array(q)-n*d)
        if z is not None:return z
    return mid
def soil_at(q,n,floor):
    for d in [.04,.10,.25]:
        z=soil.height(np.array(q)+n*d)
        if z is not None:return z
        z=surfaces.height(np.array(q)+n*d)
        if z is not None:return z
    return floor
for poly in shapely.get_parts(cuts):
    if poly.geom_type!='Polygon':continue
    for ring in [poly.exterior,*poly.interiors]:
        ring=shapely.segmentize(ring,1.25);coords=np.array(ring.coords)
        for a,b in zip(coords[:-1],coords[1:]):
            delta=b-a;L=np.linalg.norm(delta)
            if L<1e-7:continue
            n=np.array([delta[1],-delta[0]])/L;mid=(a+b)/2;fm=floor_at(mid,n)
            if fm is None:missing+=1;continue
            fa=floor_at(a,n,fm);fb=floor_at(b,n,fm);sa=soil_at(a,n,fa);sb=soil_at(b,n,fb)
            if max(sa-fa,sb-fb)<.012:continue
            k=len(v);v.extend([[*a,min(fa,sa)-.08],[*b,min(fb,sb)-.08],[*b,max(fb,sb)+.012],[*a,max(fa,sa)+.012]]);f.extend([[k,k+1,k+2],[k,k+2,k+3]]);segments+=1
data=bpy.data.meshes.new('Rear_Terrain_Cut_Closure');data.from_pydata(v,[],f);data.materials.append(bpy.data.materials['Bridge_Concrete']);data.update();ob=bpy.data.objects.new('Rear_Terrain_Cut_Closure_All',data);sc.collection.objects.link(ob);ob.parent=bpy.data.objects['08_BUILDING_FOOTINGS'];ob['surface_type']='terrain_cut_retaining_wall';ob['structural_connector_not_building']=True
b=json.loads((OUT/'compact_build_report.json').read_text());b['uphill_terrain_cut_closures']={'segments':segments,'triangles':len(f),'unsampled_edge_segments':missing};(OUT/'compact_build_report.json').write_text(json.dumps(b,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain their textures.')
print('V11_UPHILL_CUTS_CLOSED',segments,'triangles',len(f),'edge_samples_missing',missing,flush=True)
