"""Blend rear access aprons into the existing alley height planes without overlapping steps."""
import bpy,sys,json,argparse,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--model-dir',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--baseline',type=Path,default=ROOT/'recovery/huizhou_city_v10');ap.add_argument('--deps',type=Path,default=ROOT/'blender_deps');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
sys.path.insert(0,str(args.deps.resolve()));sys.path.insert(0,str(args.baseline.resolve()/'tools'))
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from city_surface_sampling import HeightField
OUT=args.model_dir.resolve();p=json.loads((OUT/'city_plan.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(OUT/'huizhou_road_network.blend'));bpy.context.view_layer.update();sc=bpy.context.scene
for ob in list(sc.objects):
    if ob.name.startswith(('Rear_Edge_Stitch_','Rear_Edge_Closure_')):bpy.data.objects.remove(ob,do_unlink=True)
names={a['name'] for a in p['pedestrian_alleys']};walk=HeightField([o for o in sc.objects if o.type=='MESH' and (o.name in names or o.get('surface_type')=='sidewalk')]);oldpolys=unary_union([LineString(a['points']).buffer(a['width']/2,cap_style=2) for a in p['pedestrian_alleys']]);atlas=bpy.data.materials['Road_Modular_Original_Atlas']
for row in p['rear_rows']:
    goal=np.array(row['goal']);g0=walk.height(goal);grad=[]
    for a in range(2):
        d=np.zeros(2);d[a]=.12;v0=walk.height(goal-d);v1=walk.height(goal+d);grad.append((v1-v0)/.24 if v0 is not None and v1 is not None else 0.)
    grad=np.array(grad);line=LineString(row['route']);L=line.length;face=np.array(row['face']);u=np.array(row['u']);n=np.array(row['n']);floor=row['floor']-.028;depth=.20 if row['core'] else 3.9
    fore=Polygon([face-u*.02,face+u*(row['width']+.02),face+u*(row['width']+.02)+n*depth,face-u*.02+n*depth]);crossing=line.intersection(fore);ramp_start=max([line.project(Point(q)) for part in shapely.get_parts(crossing) if part.geom_type=='LineString' for q in part.coords] or [0.]);direction=(np.array(row['route'][-1])-np.array(row['route'][-2]));direction/=np.linalg.norm(direction);join=0.
    for d in np.arange(.1,min(4.,L)+.05,.1):
        if walk.height(goal-direction*d) is None:break
        join=float(d)
    ramp_end=max(ramp_start+.2,L-join);front_distance=float(np.dot(goal-face,n)-join);aligned=abs(float(np.dot(direction,n)))>.98 and np.dot(goal-face,n)>0
    def height(xy):
        xy=np.array(xy);old=walk.height(xy)
        if old is not None:return old+.001
        s=line.project(Point(xy));t=float(np.clip((s-ramp_start)/max(.2,ramp_end-ramp_start),0,1));plane=g0+.001+float(grad@(xy-goal));infore=(-.03<float((xy-face)@u)<row['width']+.03 and -.03<float((xy-face)@n)<depth+.01)
        if infore:
            t=0.
            if aligned and 0<front_distance<depth+.05:t=float(np.clip(float((xy-face)@n)/front_distance,0,1))
        return floor*(1-t)+plane*t
    poly=Polygon(row['polygon']);pieces=[poly.difference(oldpolys),poly.intersection(oldpolys)];v=[];f=[]
    for piece in pieces:
        if piece.is_empty:continue
        for t in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(piece,1.2))):
            xy=np.array(t.exterior.coords)[:3];a=xy[1]-xy[0];b=xy[2]-xy[0]
            if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
            k=len(v);v.extend([[*q,height(q)] for q in xy]);f.append([k,k+1,k+2])
    ob=bpy.data.objects[row['name']+'_Entry_Walk'];data=bpy.data.meshes.new(ob.name+'_Graded');data.from_pydata(v,[],f);data.materials.append(atlas);data.update();uv=data.uv_layers.new(name='UVMap')
    for face0 in data.polygons:
        for li in face0.loop_indices:
            q=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(.216+.055*((q.x/3)%1),.5989+.1777*((q.y/16.9048)%1))
    ob.data=data;edges=bpy.data.objects[row['name']+'_Walk_Retaining_Edges']
    for i,q in enumerate(edges.data.vertices):
        top=height(q.co[:2])-.012
        if i%4 in [2,3]:q.co.z=top
        else:q.co.z=min(q.co.z,top-.18)
    edges.data.update();row['goal_surface_gradient']=grad.tolist();row['ramp_start_m']=ramp_start;row['ramp_end_m']=ramp_end
    print('REAR_ACCESS_GRADED',row['name'],flush=True)
(OUT/'city_plan.json').write_text(json.dumps(p,separators=(',',':')))
b=json.loads((OUT/'compact_build_report.json').read_text());b['rear_aprons_match_existing_alley_planes']=True;(OUT/'compact_build_report.json').write_text(json.dumps(b,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain their textures.')
print('V11_ACCESS_GRADING_DONE',flush=True)
