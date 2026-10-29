import os
"""Independent static checks: counts, source fidelity, floors, overlaps,
foundation/apron coplanarity, unchanged street geometry and source grouping."""
import bpy,sys,json,hashlib,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')));sys.path.insert(0,str(R/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v16.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));old=json.load(open(R/'baseline/city_plan.json'));build=json.load(open(R/'model/build_report.json'));levels=json.load(open(R/'model/site_levels.json'));fails=[]
def check(ok,k,detail=None):
 if not ok:fails.append({'check':k,'detail':detail})
def hashgeom(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([v.uv[:] for v in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
def co(o):
 c=np.array([v.co[:] for v in o.data.vertices]);M=np.array(o.matrix_world);return c@M[:3,:3].T+M[:3,3]
for n,h in build['unchanged_original_objects'].items():check(n in sc.objects and hashgeom(sc.objects[n])==h,'unchanged_baseline_object',n)
for k in ['coasts','lake','nodes','edges','interchanges','pedestrian_alleys']:check(p[k]==old[k],'unchanged_'+k)
check(p['cbd_plan']['tianming']==old['cbd_plan']['tianming'],'tianming_preserved');check(len(p['buildings'])+len(p['real_buildings'])==664,'city_count')
check(sum(r.get('zone')=='CBD' for r in p['real_buildings'])==32,'CBD_32');apt=[r for r in p['real_buildings'] if r.get('zone')=='APARTMENT'];gov=[r for r in p['real_buildings'] if r.get('zone')=='GOVERNMENT'];check(len(apt)==12,'apartments_12');check(len(gov)==3 and sum(b['zone']=='GOVERNMENT' for b in p['buildings'])==4,'government_7');check(p['urban_areas_v14']['municipal_campus']['area_m2']<old['urban_areas_v14']['municipal_campus']['area_m2'],'compact_campus')
groups={g:[r for r in apt if r['asset_color_group']==g] for g in ['YELLOW_50','PINK_53','GRAY_54']};check(all(len(v)==4 for v in groups.values()),'four_each_color');check(max(r['center'][0] for r in groups['YELLOW_50'])<min(r['center'][0] for r in groups['PINK_53']) and max(r['center'][0] for r in groups['PINK_53'])<min(r['center'][0] for r in groups['GRAY_54']),'contiguous_color_groups')
allpoly=[(r.get('name',r.get('instance_name')),Polygon(r.get('footprint',r.get('footprint_xy')))) for r in p['buildings']+p['real_buildings']];land=Polygon(p['coasts']['MAIN']);reserve=Polygon(p['cbd_plan']['tianming']['polygon']);roadfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.02) for e in p['edges']]);terrain=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);sourcechecks=[];floorchecks=[]
for level in levels:
 name=level['name'];poly=Polygon(level['poly']);check(land.covers(poly),'on_land',name);check(poly.intersection(roadfull).area<.001,'clear_of_roads',name);check(poly.intersection(reserve).area<.001,'reserve_clear',name);over=[n for n,q in allpoly if n!=name and poly.intersection(q).area>.01];check(not over,'building_overlap',[name,over])
 obs=[o for o in sc.objects if o.type=='MESH' and o.get('source_instance')==name]
 if obs:
  vertices=np.concatenate([co(o) for o in obs]);height=float(np.ptp(vertices[:,2]));bottom=float(vertices[:,2].min());check(abs(height-level['height'])<.003,'source_height',[name,height]);check(abs(bottom-level['floor'])<.005,'source_floor',[name,bottom,level['floor']]);check(all(o.data.uv_layers for o in obs),'source_UV',name)
  if name.startswith(('APT_V16','GOV_V16')):
   scale=np.linalg.norm(np.array(obs[0].matrix_world)[:3,:3],axis=0);check(np.ptp(scale)<1e-5 and np.linalg.det(np.array(obs[0].matrix_world)[:3,:3])>0,'uniform_nonmirror_scale',name)
  sourcechecks.append({'name':name,'height_m':height,'floor_m':bottom})
 delta=[];missing=0
 for q in shapely.segmentize(poly.buffer(.12,join_style=2).exterior,1.5).coords:
  h=terrain.height(q)
  if h is None:missing+=1;continue
  delta.append(level['floor']-h)
 check(not missing,'site_ground_continuous',[name,missing]);check(not delta or min(delta)>-.035,'no_building_sinking',[name,min(delta,default=0)]);check(not delta or max(delta)<.30,'entrance_ground_height',[name,max(delta,default=0)]);floorchecks.append({'name':name,'missing_ground_samples':missing,'minimum_floor_above_ground_m':min(delta,default=0),'maximum_floor_above_ground_m':max(delta,default=0)})
# Top overlap check uses projected geometry only at exactly matching elevations.
coplanar=[]
for o in sc.objects:
 if o.type!='MESH' or not o.get('source_object','').endswith('_Foundation'):continue
 name=o['source_object'][:-len('_Foundation')];walks=[w for w in sc.objects if w.type=='MESH' and w.get('source_object','').startswith(name+'_') and w.get('surface_type')=='v15_access_walk']
 if not walks:continue
 c=co(o);o.data.calc_loop_triangles();top=c[:,2].max();F=unary_union([Polygon(c[list(t.vertices),:2]) for t in o.data.loop_triangles if np.ptp(c[list(t.vertices),2])<.001 and abs(c[list(t.vertices),2].mean()-top)<.001]);W=[]
 for w in walks:
  wc=co(w);w.data.calc_loop_triangles();W.extend(Polygon(wc[list(t.vertices),:2]) for t in w.data.loop_triangles if np.ptp(wc[list(t.vertices),2])<.001 and abs(wc[list(t.vertices),2].mean()-top)<.001)
 area=F.intersection(unary_union(W)).area
 if area>.02:coplanar.append({'name':name,'overlap_m2':area})
check(not coplanar,'coplanar_black_rim_removed',coplanar)
pathchecks=[]
for w in p['access_v16']:
 line=LineString(w['route']);heights=[];missing=0
 for d in np.linspace(.04,max(.05,line.length-.8),max(5,int(line.length/.5))):
  q=line.interpolate(d).coords[0];h=terrain.height(q)
  if h is None:missing+=1
  else:heights.append((d,h))
 grade=max([abs(h1-h0)/(d1-d0) for (d0,h0),(d1,h1) in zip(heights[:-1],heights[1:])],default=0.)
 # Endpoint samples can lie on the retained public sidewalk rather than terrain.
 check(missing<=8,'graded_access_continuous',[w['name'],missing]);check(grade<.35,'graded_access_slope',[w['name'],grade]);pathchecks.append({'name':w['name'],'maximum_sampled_grade':grade,'samples_not_on_terrain':missing})
report={'status':'PASS' if not fails else 'FAIL','changed_districts':[6,7,8],'city_buildings':664,'cbd_buildings':32,'apartment_instances':12,'apartment_types':3,'instances_per_type':4,'municipal_buildings':7,'municipal_area_before_m2':build['municipal_area_before_m2'],'municipal_area_after_m2':build['municipal_area_after_m2'],'preserved_baseline_objects':len(build['unchanged_original_objects']),'source_checks':sourcechecks,'floor_checks':floorchecks,'remaining_coplanar_foundations':coplanar,'path_checks':pathchecks,'failures':fails,'limits':'Static model geometry checks. Runtime navigation, collision and traffic are outside this district asset update.'}
(R/'validation').mkdir(exist_ok=True);(R/'validation/native_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('VALIDATION',report['status'],json.dumps(fails),flush=True);assert not fails,fails
