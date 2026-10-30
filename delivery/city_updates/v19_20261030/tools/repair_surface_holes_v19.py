"""Fill actual uncovered terrain slivers at road-kit edges, without stacked surfaces."""
import sys,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'));sys.path.insert(0,str(R/'tools'))
import bpy,numpy as np,shapely
from mathutils import Vector
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));obs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk','pavement','road_kit','curb']];field=HeightField(obs)
raw=unary_union([Polygon(s['pad']).buffer(8,join_style=2) for s in sites]+[Polygon(b['footprint']).buffer(3,join_style=2) for b in layout['removed_placeholder_lots']]+[Polygon(g['court']) for g in layout['groups']]+[Polygon(w['polygon']).buffer(3,join_style=2) for w in p['access_v19']]);land=unary_union([Polygon(v) for v in p['coasts'].values()]);bodies=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))).buffer(.03,join_style=2) for b in p['buildings']+p['real_buildings']]);wanted=raw.intersection(land).difference(bodies);cover=[]
for o in obs:
 o.data.calc_loop_triangles();xyz=co(o);fs=np.array([t.vertices[:] for t in o.data.loop_triangles],np.int32)
 if not len(fs):continue
 q=xyz[fs,:2];det=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);q=q[np.abs(det)>1e-8]
 if not len(q):continue
 shapes=shapely.polygons(q);ix=shapely.intersects(shapes,wanted);cover.append(shapely.union_all(shapes[ix]))
 print('COVER',o.name,flush=True)
covered=unary_union(cover);missing=wanted.difference(covered);parts=[g for g in shapely.get_parts(missing) if g.geom_type=='Polygon' and g.area>=.005];verts={d:[] for d in [4,8,9,14]};faces={d:[] for d in verts};mats={d:[] for d in verts};roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.15,join_style=2) for e in p['edges']])
def district(q):return 9 if q[0]<-700 and q[1]<0 else 14 if q[0]>450 and q[1]<0 else 4 if q[1]<620 else 8
def z(q):
 value=field.height(q)
 if value is not None:return value
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));t=field.tri[idx];w=np.linalg.solve(np.vstack([t[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);return float(w@t[:,2])
for part in parts:
 for t in shapely.get_parts(shapely.constrained_delaunay_triangles(part)):
  xy=np.array(t.exterior.coords)[:3]
  if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
  mid=xy.mean(0);d=district(mid);k=len(verts[d]);verts[d].extend([[float(q[0]),float(q[1]),z(q)] for q in xy]);faces[d].append([k,k+1,k+2]);mats[d].append(1 if roads.covers(Point(mid)) else 2 if d==14 else 0)
new=[]
for d in verts:
 if not faces[d]:continue
 name=f'V19_Closed_Surface_Seams_{d:02}';m=bpy.data.meshes.new(name);m.from_pydata(verts[d],[],faces[d]);m.materials.append(bpy.data.materials['V19_Landscape']);m.materials.append(bpy.data.materials['V19_Warm_Pavers']);m.materials.append(bpy.data.materials['V19_Service_Gravel']);m.polygons.foreach_set('material_index',np.array(mats[d],np.int32));m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=bpy.data.objects[f'District_{d:02}'];o['district_id']=d;o['surface_type']='terrain';o['source_object']=name;o['modified_in_version']='v19';o['surface_seam_repair']=True;new.append(name)
filled=unary_union(parts);remaining=wanted.difference(covered.union(filled));large=[g.area for g in shapely.get_parts(remaining) if g.geom_type=='Polygon' and g.area>=.005];report={'status':'PASS' if not large else 'FAIL','method':'actual projected surface coverage; fill only uncovered polygons; boundary heights sampled from adjacent surfaces','polygons_filled':len(parts),'filled_area_m2':filled.area,'triangles':sum(len(x) for x in faces.values()),'remaining_large_holes_m2':large,'maximum_unfilled_fragment_m2':max([g.area for g in shapely.get_parts(remaining) if g.geom_type=='Polygon'],default=0)};(R/'validation/surface_coverage_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));p['urban_areas_v19']['surface_seam_repair']=report;(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));br=json.load(open(R/'model/build_report.json'));br['new_objects'].extend(new);br['surface_seam_repair']=report;(R/'model/build_report.json').write_text(json.dumps(br,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v19.blend'),compress=True);print('SURFACE_SEAMS',json.dumps(report),flush=True)
