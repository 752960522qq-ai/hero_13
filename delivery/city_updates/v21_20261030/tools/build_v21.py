"""Add each of the 22 newly extracted buildings once, with provenance and graded sites."""
from pathlib import Path
import sys,json,math,copy,hashlib,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from mathutils import Matrix,Vector
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co,fingerprint,keep_faces,clip_ground
layout=json.load(open(R/'layout.json'));p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);cat={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))};ids=layout['changed_district_ids'];assert len(layout['placements'])==len(cat)==len({b['asset_id'] for b in layout['placements']})
cached=R.parent/'work_v20/model/city_v20.blend'
if cached.exists():bpy.ops.wm.open_mainfile(filepath=str(cached))
else:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.data.orphans_purge(do_recursive=True);bpy.context.view_layer.update();sc=bpy.context.scene;roots={d:bpy.data.objects[f'District_{d:02}'] for d in ids};before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
terrain=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'];walks=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'];roadobs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['pavement','road_kit']];soil=HeightField(terrain);walkfield=HeightField(walks);streetfield=HeightField(roadobs)
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 i=int(field.planar_tree.nearest(Point(q)));tri=field.tri[i];from shapely.ops import nearest_points
 hit=np.array(nearest_points(field.planar[i],Point(q))[0].coords[0]);w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[hit,1]);return float(w@tri[:,2])
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
removed={b['name'] for b in layout['removed_placeholder_lots']};lotpolys=[Polygon(b['footprint']) for b in old['buildings']];lottree=shapely.STRtree(lotpolys);removed_faces=0
for o in list(sc.objects):
 if o.type!='MESH':continue
 source=o.get('source_object',o.name)
 if any(name in source for name in removed):bpy.data.objects.remove(o,do_unlink=True);continue
 if o.get('is_placeholder'):
  xyz=co(o);keep=[];owners=set()
  for f in o.data.polygons:
   point=Point(xyz[list(f.vertices),:2].mean(0));i=int(lottree.nearest(point));owner=old['buildings'][i]['name'];assert point.distance(lotpolys[i])<.12,(o.name,owner);keep.append(owner not in removed)
   if owner not in removed:owners.add(owner)
  if not all(keep):
   removed_faces+=len(keep)-sum(keep);name=o.name;keep_faces(o,keep)
   if name in sc.objects:sc.objects[name]['placeholder_lot_count']=len(owners);sc.objects[name]['modified_in_version']='v21'
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed]
for k,v in list(p.items()):
 if k.startswith('access_') and isinstance(v,list):p[k]=[r for r in v if r.get('building',r.get('name')) not in removed]
lands=unary_union([Polygon(v) for v in p['coasts'].values()]);fixed=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon']);oldfull=unary_union([LineString(np.asarray(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in p['edges']]);oldcar=unary_union([LineString(np.asarray(e['points'])[:,:2]).buffer(e['carriage_width']/2,join_style=2) for e in p['edges']])
templates={}
for aid in sorted(cat):
 start=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'extracted'/cat[aid]['file']));bpy.context.view_layer.update();obs=set(sc.objects)-start;meshes=[]
 for o in obs:
  if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);m.update();meshes.append((o.get('source_mesh_name',o.name),m))
 for o in obs:bpy.data.objects.remove(o,do_unlink=True)
 templates[aid]=meshes
sites=[];paths=[]
for b in layout['placements']:
 a=cat[b['asset_id']];route=LineString(b['entrance_route']);goal=np.array(route.coords[-1]);endz=walkfield.height(goal)
 if endz is None:endz=nearest(streetfield,goal)+.12
 floor=float(endz+.02);poly=Polygon(b['footprint_xy']);pad=poly.buffer(.32,join_style=2);rec={**b,'floor':floor,'poly':poly,'pad':pad};sites.append(rec);M=Matrix.Translation((*b['center'],floor))@Matrix.Rotation(math.radians(b['rotation_deg']),4,'Z')@Matrix.Diagonal((b['scale'],b['scale'],b['scale'],1))
 for i,(sn,mesh) in enumerate(templates[b['asset_id']]):
  o=bpy.data.objects.new(f"{b['instance_id']}__Part{i:03}",mesh);sc.collection.objects.link(o);o.parent=roots[b['district_id']];o.matrix_world=M
  fields=dict(district_id=b['district_id'],asset_id=b['asset_id'],instance_id=b['instance_id'],source_instance=b['instance_id'],source_id=b['source_id'],source_filename=b['source_filename'],source_node_name=b['source_node_name'],source_mesh_name=sn,source_sha256=b['source_sha256'],replaces_lots='|'.join(b['replaces']),layout_group=b['group'],added_in_version='v21',geometry_status=a['geometry_status'],quality_label_zh=a['quality_label_zh'],issue_note_zh=a['issue_note_zh'],maximum_instances_per_asset=1,texture_enhanced=a.get('texture_enhanced',False))
  for k,v in fields.items():o[k]=v
 band=route.buffer(.65,cap_style=2,join_style=2);paths.append(dict(name=b['name']+'_Entrance',building=b['name'],route=route,polygon=band,profile=[[0,floor-.004],[route.length,float(endz)]],region=b['region'],street=b['street']))
 print('BUILT',b['name'],round(floor,3),a['quality_label_zh'],flush=True)
def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.88;return m
mats={k:material('V21_'+k,c) for k,c in dict(land=(.34,.41,.25),paver=(.51,.50,.45),foundation=(.48,.47,.42)).items()}
def newmesh(name,vertices,faces,mat,d,props=None):
 if not faces:return None
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.materials.append(mat);me.update();o=bpy.data.objects.new(name,me);sc.collection.objects.link(o);o.parent=roots[d];o['district_id']=d;o['source_object']=name;o['modified_in_version']='v21'
 for k,v in (props or {}).items():o[k]=v
 return o
holes=unary_union([s['poly'] for s in sites]);pads=unary_union([s['pad'] for s in sites]);pathshape=unary_union([w['polygon'] for w in paths]).difference(holes);raw=unary_union([s['pad'].buffer(5.5,join_style=2) for s in sites]+[w['polygon'].buffer(2.5) for w in paths]+[Polygon(b['footprint']).buffer(2) for b in layout['removed_placeholder_lots']]).intersection(lands).difference(fixed.buffer(.04)).difference(reserve).difference(oldfull);aprons=pads.difference(holes).difference(oldfull).union(pathshape.difference(oldcar));land=raw.difference(pads).difference(pathshape);cut=raw.union(holes).union(aprons)
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain':clip_ground(o,cut)
cache={}
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def topz(q):
 key=tuple(round(float(x),7) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(soil,q)
 for s in sites:
  dist=pt.distance(s['pad'])
  if dist<5.5:
   t=smooth(1-dist/5.5);z=z*(1-t)+(s['floor']-.01)*t
 for w in paths:
  dist=pt.distance(w['route'])
  if dist<2.5:
   h=float(np.interp(w['route'].project(pt),*np.asarray(w['profile']).T));t=smooth(1-max(0,dist-.65)/1.85);z=z*(1-t)+h*t
 owners=[s for s in sites if s['pad'].buffer(.00001).covers(pt)]
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.004
 # Terrain meets every original pavement at its measured original height.
 distance=pt.distance(oldfull)
 if distance<.4:
  hit=shapely.ops.nearest_points(oldfull,pt)[0];original=walkfield.height(hit.coords[0]);original=nearest(soil,q) if original is None else original;t=smooth(1-distance/.4);z=z*(1-t)+original*t
 # Entrance ramps continue through the entire verge to the measured old walk.
 active=[w for w in paths if w['polygon'].buffer(.00001).covers(pt)]
 if active:
  w=min(active,key=lambda w:pt.distance(w['route']));z=float(np.interp(w['route'].project(pt),*np.asarray(w['profile']).T))
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.004
 cache[key]=z;return z
def surface(name,shape,fn,mat,stype,step):
 vv={d:[] for d in ids};ff={d:[] for d in ids}
 for part in shapely.get_parts(shape):
  if part.is_empty or part.area<1e-8:continue
  x0,y0,x1,y1=part.bounds;xs=sorted(set(np.arange(math.floor(x0/step)*step,x1+step,step).tolist()+[-950.]));ys=sorted(set(np.arange(math.floor(y0/step)*step,y1+step,step).tolist()+[620.]));xs=[x for x in xs if x0-step<=x<=x1+step];ys=[y for y in ys if y0-step<=y<=y1+step]
  for x,xn in zip(xs,xs[1:]):
   for y,yn in zip(ys,ys[1:]):
    tile=box(x,y,xn,yn)
    if not part.intersects(tile):continue
    for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(part.intersection(tile))):
     xy=np.asarray(triangle.exterior.coords)[:3]
     if abs(np.linalg.det(np.c_[xy,np.ones(3)]))<1e-9:continue
     if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
     d=district(xy.mean(0));assert d in ids,(name,d);k=len(vv[d]);vv[d].extend([[float(a),float(b),float(fn([a,b]))] for a,b in xy]);ff[d].append([k,k+1,k+2])
 for d in ids:newmesh(name+f'_{d:02}',vv[d],ff[d],mat,d,dict(surface_type=stype,walkable_surface=True))
 print('SURFACE',name,round(shape.area,1),sum(len(f) for f in ff.values()),flush=True)
surface('V21_Graded_Land',land,topz,mats['land'],'terrain',3.5);surface('V21_Entrance_Aprons',aprons,topz,mats['paver'],'sidewalk',1)
for s in sites:
 xy=np.asarray(shapely.orient_polygons(s['poly']).exterior.coords)[:-1];n=len(xy);bottom=min([nearest(soil,q) for q in xy]+[s['floor']-.3])-.1;v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,s['floor']-.008)]];faces=[]
 for i in range(1,n-1):faces.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;faces.extend([[i,j,j+n],[i,j+n,i+n]])
 newmesh(s['name']+'_Foundation',v.tolist(),faces,mats['foundation'],s['district_id'],dict(site_building=s['name'],is_site_foundation=True,placement_ground_only=True))
# Canonicalize equal packed image bytes, including the one enhanced atlas shared by all S09 models.
canonical={};rebindings=0
for image in list(bpy.data.images):
 if not image.packed_file:continue
 key=(hashlib.sha256(image.packed_file.data).hexdigest(),image.colorspace_settings.name)
 if key in canonical:
  for mat in bpy.data.materials:
   if mat.use_nodes:
    for node in mat.node_tree.nodes:
     if node.type=='TEX_IMAGE' and node.image==image:node.image=canonical[key];rebindings+=1
 else:canonical[key]=image
for image in list(bpy.data.images):
 if image.users==0:bpy.data.images.remove(image)
def serial(s):return {k:list(v.exterior.coords) if k in ['poly','pad','polygon'] else list(v.coords) if k=='route' else v for k,v in s.items()}
p['real_buildings'].extend([serial(s) for s in sites]);p['access_v21']=[serial(w) for w in paths];p['urban_areas_v21']=dict(groups=layout['groups'],maximum_instances_per_new_asset=1,open_model_policy=layout['policy'],source_ids=sorted({b['source_id'] for b in sites}));p['schema']='hero13.city.source-expansion.v21';counts=collections.Counter(b['zone'] for b in p['buildings']);counts.update(b.get('zone','OLDTOWN') for b in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),building_count_by_zone=dict(counts),new_v21_buildings=len(sites),source_asset_types=len({b.get('asset_id',b.get('file')) for b in p['real_buildings']}));p['stats']['building_footprint_area_m2']=sum(Polygon(b.get('footprint',b.get('footprint_xy'))).area for b in p['buildings']+p['real_buildings']);p['stats']['building_coverage_percent']=p['stats']['building_footprint_area_m2']/p['stats']['land_area_m2']*100
nt=p['urban_areas_v18']['new_town'];boundary=Polygon(nt['polygon']);inside=[b for b in p['real_buildings'] if boundary.covers(Polygon(b['footprint_xy']))];nt['new_source_buildings']=[b.get('instance_id',b.get('instance_name',b.get('name'))) for b in inside];nt['new_source_building_units']=len(inside);nt['building_units']=len(inside)+nt['existing_residential_units'];nt['updated_in_version']='v21';p['stats']['new_town_buildings']=nt['building_units'];assert p['stats']['buildings']==layout['city_building_units']<700
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
for name,h in before.items():
 if name in after and h!=after[name]:sc.objects[name]['modified_in_version']='v21'
report=dict(version='v21',baseline_commit=layout['baseline_commit'],changed_district_ids=ids,new_asset_types=len(cat),new_asset_instances=len(sites),maximum_instances_per_new_asset=1,instances_by_source=dict(collections.Counter(b['source_id'] for b in sites)),city_buildings=p['stats']['buildings'],removed_placeholders=sorted(removed),removed_placeholder_faces=removed_faces,unchanged_original_objects={n:h for n,h in before.items() if after.get(n)==h},changed_original_objects=[n for n,h in before.items() if n in after and after[n]!=h],removed_original_objects=sorted(set(before)-set(after)),new_objects=sorted(set(after)-set(before)),ground_patch_m2=raw.area,image_node_rebindings=rebindings)
for path,data in [('city_plan.json',p),('site_levels.json',[serial(s) for s in sites]),('build_report.json',report),('entrances.json',[serial(w) for w in paths])]:
 (R/'model'/path).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v21.blend'),compress=True);print('V21_BUILD_COMPLETE',len(sites),p['stats']['buildings'],flush=True)
