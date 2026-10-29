"""Close access-side retaining edges and batch every site's walking mesh."""
import bpy,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,'/workspace/scratch/705f52588668/tools_runtime/blender_deps')
from city_surface_sampling import HeightField
from shapely.geometry import Polygon,Point
import shapely
bpy.ops.wm.open_mainfile(filepath='/workspace/scratch/705f52588668/work_v14/model/huizhou_road_network.blend')
oldsoil=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/huizhou_road_network.blend'));p=json.loads((ROOT/'model/city_plan.json').read_text());sc=bpy.context.scene
if bpy.data.objects.get('V15_Access_Retaining_Sides'):bpy.data.objects.remove(bpy.data.objects['V15_Access_Retaining_Sides'],do_unlink=True)
vv=[];ff=[];unresolved=[]
for w in p['access_v15']:
    name=w['building'];parts=[o for o in sc.objects if o.type=='MESH' and o.name.startswith(name+'_') and (o.get('surface_type') in ['v15_site_apron','v15_access_walk'] or '_Stair_' in o.name)]
    field=HeightField(parts);poly=shapely.orient_polygons(Polygon(w['polygon']),exterior_cw=False);ring=np.array(shapely.segmentize(poly.exterior,.45).coords)
    for aa,bb in zip(ring[:-1],ring[1:]):
        delta=bb-aa;d=np.linalg.norm(delta)
        if d<1e-8:continue
        n=np.array([delta[1],-delta[0]])/d;mid=(aa+bb)/2;h=field.height(mid-n*.03)
        if h is None:
            hit,_,idx,distance=field.tree.find_nearest(Vector((*mid,0)))
            if distance>.18:unresolved.append({'building':name,'xy':mid.tolist(),'distance':distance});continue
            tri=field.tri[idx];weights=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);h=float(weights@tri[:,2])
        zs=[]
        for q in [aa,bb]:
            z=oldsoil.height(q+n*.06)
            if z is None:
                hit,_,idx,distance=oldsoil.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=oldsoil.tri[idx];weights=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);z=float(weights@tri[:,2])
            zs.append(z)
        if max(abs(z-h) for z in zs)<.025:continue
        k=len(vv);vv.extend([[*aa,min(zs[0],h)-.08],[*bb,min(zs[1],h)-.08],[*bb,h-.004],[*aa,h-.004]]);ff.extend([[k,k+1,k+2],[k,k+2,k+3]])
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    active=next((o for o in parts if o.name==w['name']),parts[0]);bpy.context.view_layer.objects.active=active
    bpy.ops.object.join();joined=bpy.context.object;joined.name=w['name'];joined['surface_type']='v15_access_walk';joined['site_building']=name
    print('SITE_ACCESS_BATCHED',name,len(parts),len(joined.data.polygons),flush=True)
m=bpy.data.meshes.new('V15_Access_Retaining_Sides');m.from_pydata(vv,[],ff);m.materials.append(bpy.data.materials['Bridge_Concrete']);m.update();o=bpy.data.objects.new(m.name,m);sc.collection.objects.link(o);o.parent=bpy.data.objects['08_BUILDING_FOOTINGS'];o['surface_type']='terrain_cut_retaining_wall'
(ROOT/'model/v15_finish_report.json').write_text(json.dumps({'access_sites_batched':len(p['access_v15']),'retaining_triangles':len(ff),'unresolved_access_rim_segments':unresolved},indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/huizhou_road_network.blend'),compress=True)
print('V15_FINISH_DONE',len(ff),len(unresolved),flush=True)
