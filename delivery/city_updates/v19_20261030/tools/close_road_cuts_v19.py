"""Close the vertical gap between graded land and lower sidewalks at road cut edges."""
import sys,json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'));sys.path.insert(0,str(R/'tools'))
import bpy,numpy as np,shapely
from mathutils import Vector
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));walk=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.08,join_style=2) for e in p['edges']]);aprons=unary_union([Polygon(w['polygon']).buffer(.15,join_style=2) for w in p['access_v19']]);vv={d:[] for d in [4,8,9,14]};ff={d:[] for d in vv};segments=[]
for o in list(sc.objects):
 if o.type!='MESH' or not(o.name.startswith('V19_Graded_Ground_') or o.get('surface_seam_repair')):continue
 xyz=co(o);o.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in o.data.loop_triangles],np.int32);points,inverse=np.unique(np.round(xyz,5),axis=0,return_inverse=True);tri=inverse[tri];edges=np.r_[tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]];edges.sort(axis=1);edges,counts=np.unique(edges,axis=0,return_counts=True);d=int(o['district_id'])
 for e in edges[counts==1]:
  q=points[e];mid=q[:,:2].mean(0);pt=Point(mid)
  if not roads.covers(pt) or aprons.covers(pt):continue
  lower=[]
  for a in q:
   hit,_,idx,dist=walk.tree.find_nearest(Vector((float(a[0]),float(a[1]),0)));t=walk.tri[idx];w=np.linalg.solve(np.vstack([t[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);z=float(w@t[:,2]);lower.append([float(hit.x),float(hit.y),z-.025])
  gap=np.array(q)[:,2]-np.array(lower)[:,2]
  if max(np.abs(gap))<.12 or any(np.linalg.norm(a[:2]-np.array(b[:2]))>3.5 for a,b in zip(q,lower)):continue
  k=len(vv[d]);vv[d].extend([q[0].tolist(),q[1].tolist(),lower[1],lower[0]]);ff[d].extend([[k,k+1,k+2],[k,k+2,k+3]]);segments.append({'district_id':d,'top':q.tolist(),'bottom':[lower[0],lower[1]]})
new=[]
for d in vv:
 if not ff[d]:continue
 name=f'V19_Light_Road_Cut_Closures_{d:02}';m=bpy.data.meshes.new(name);m.from_pydata(vv[d],[],ff[d]);m.materials.append(bpy.data.materials['V19_Foundation']);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=bpy.data.objects[f'District_{d:02}'];o['district_id']=d;o['surface_type']='road_cut_retaining_wall';o['source_object']=name;o['modified_in_version']='v19';new.append(name)
report={'status':'PASS','segments':len(segments),'triangles':sum(len(x) for x in ff.values()),'method':'boundary edge land-to-sidewalk closures, with entrance corridors kept clear'};(R/'validation/road_cut_closure_validation.json').write_text(json.dumps(report,indent=2));p['urban_areas_v19']['road_cut_closures']=report;(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));br=json.load(open(R/'model/build_report.json'));br['new_objects'].extend(new);br['road_cut_closures']=report;(R/'model/build_report.json').write_text(json.dumps(br,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v19.blend'),compress=True);print('ROAD_CUT_CLOSURES',report,flush=True)
