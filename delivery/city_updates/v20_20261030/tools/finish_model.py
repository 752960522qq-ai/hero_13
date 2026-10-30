from pathlib import Path
import json,sys,hashlib,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from mathutils import Matrix
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v20.blend'));bpy.context.view_layer.update();props=json.load(open(R/'model/public_instances.json'));byid={p['instance_id']:p for p in props};sc=bpy.context.scene
p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));car=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.5,join_style=2) for e in p['edges']]);buildings=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings']]).buffer(.6);entrances=unary_union([Polygon(w['polygon']) for w in p['access_v20']]).buffer(.55);field=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk','pavement']])
def cylinder(v,f,a,b,r,n=8):
 a=np.array(a,dtype=float);b=np.array(b,dtype=float);z=b-a;z/=np.linalg.norm(z);u=np.cross(z,[0,0,1])
 if np.linalg.norm(u)<.01:u=np.array([1.,0,0])
 u/=np.linalg.norm(u);w=np.cross(z,u);k=len(v)
 for c in [a,b]:
  for t in np.linspace(0,2*math.pi,n,endpoint=False):v.append((c+r*(math.cos(t)*u+math.sin(t)*w)).tolist())
 f.extend([[k+i for i in range(n-1,-1,-1)],[k+n+i for i in range(n)]])
 for i in range(n):j=(i+1)%n;f.append([k+i,k+j,k+j+n,k+i+n])
for name,color in [('V20_Utility_Pole',(.43,.42,.36)),('V20_Cable',(.035,.04,.042))]:
 if name not in bpy.data.materials:
  mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85
v=[];f=[];cylinder(v,f,[0,0,0],[0,0,8.4],.135,10);cylinder(v,f,[-1,0,7.9],[1,0,7.9],.07)
for x in [-.72,0,.72]:cylinder(v,f,[x,0,7.92],[x,0,8.18],.065)
polemesh=bpy.data.meshes.new('V20_Public_Utility_Template');polemesh.from_pydata(v,[],f);polemesh.materials.append(bpy.data.materials['V20_Utility_Pole']);polemesh.update()
newpolecount=0
for r in layout['new_roads']:
 if r['region']!='WEST':continue
 line=LineString(r['points']);row=[]
 for ss in np.arange(17,line.length-15,20):
  center=np.array(line.interpolate(ss).coords[0]);t=np.array(line.interpolate(ss+.5).coords[0])-np.array(line.interpolate(ss-.5).coords[0]);t/=np.linalg.norm(t);normal=np.array([-t[1],t[0]]);q=center+normal*(r['carriage_width']/2+1.15);pt=Point(q)
  if car.intersects(pt.buffer(.16)) or buildings.intersects(pt.buffer(.25)) or entrances.intersects(pt.buffer(.3)):continue
  if any('center' in x and pt.distance(Point(x['center']))<(2.2 if x['type']=='tree' else 1.15) for x in props):continue
  z=field.height(q)
  if z is None:continue
  iid=f'V20-P{max([int(x["instance_id"].split("-P")[1]) for x in props if "-P" in x["instance_id"]],default=0)+1:03}';d=9 if q[0]<-950 else 10;ob=bpy.data.objects.new(iid+'__utility_pole',polemesh);sc.collection.objects.link(ob);ob.parent=bpy.data.objects[f'District_{d:02}'];angle=math.degrees(math.atan2(t[1],t[0]));rec=dict(instance_id=iid,type='utility_pole',center=q.tolist(),z=float(z),rotation_deg=angle,scale=1,district_id=d,group='WEST_MARKET_STREET',source='native low polygon geometry v20',building_count_units=0);props.append(rec);byid[iid]=rec;row.append(rec);newpolecount+=1
  for k,val in dict(district_id=d,public_instance_id=iid,public_type='utility_pole',layout_group='WEST_MARKET_STREET',added_in_version='v20',source_asset_id='NATIVE-V20-utility_pole',source_filename='procedural_public_furniture_v20',building_count_units=0).items():ob[k]=val
 for a,b in zip(row,row[1:]):
  if np.linalg.norm(np.array(a['center'])-b['center'])>43:continue
  iid=f'V20-C{1+sum(x["type"]=="overhead_cable" for x in props):02}';d=a['district_id'];me=bpy.data.meshes.new(iid);me.from_pydata([[0,0,0],[.01,0,0],[0,.01,0]],[],[[0,1,2]]);me.materials.append(bpy.data.materials['V20_Cable']);ob=bpy.data.objects.new(iid,me);sc.collection.objects.link(ob);ob.parent=bpy.data.objects[f'District_{d:02}']
  for k,val in dict(district_id=d,public_instance_id=iid,public_type='overhead_cable',source_asset_id='NATIVE-V20-overhead_cable',building_count_units=0).items():ob[k]=val
  props.append(dict(instance_id=iid,type='overhead_cable',start=a['instance_id'],end=b['instance_id'],minimum_cable_height_m=7.46,district_id=d,group='WEST_MARKET_STREET',building_count_units=0))
assert newpolecount>=4,newpolecount
# Cross arms and parallel conductors run across, then along, the utility row.
for p in props:
 if p['type']=='utility_pole':
  p['rotation_deg']+=90;M=Matrix.Translation((*p['center'],p['z']))@Matrix.Rotation(math.radians(p['rotation_deg']),4,'Z')
  for o in sc.objects:
   if o.get('public_instance_id')==p['instance_id']:o.matrix_world=M
for p in props:
 if p['type']!='overhead_cable':continue
 a=byid[p['start']];b=byid[p['end']];aa=np.array([*a['center'],a['z']+8.18]);bb=np.array([*b['center'],b['z']+8.18]);delta=bb[:2]-aa[:2];delta/=np.linalg.norm(delta);cross=np.array([-delta[1],delta[0]]);v=[];f=[]
 for offset in [-.68,.68]:
  previous=None
  for t in np.linspace(0,1,13):
   c=aa*(1-t)+bb*t;c[:2]+=cross*offset;c[2]-=4*.72*t*(1-t)
   if previous is not None:
    z=c-previous;z/=np.linalg.norm(z);u=np.cross(z,[0,0,1]);u/=np.linalg.norm(u);w=np.cross(z,u);k=len(v)
    for q in [previous,c]:
     for theta in np.linspace(0,2*math.pi,5,endpoint=False):v.append((q+.018*(math.cos(theta)*u+math.sin(theta)*w)).tolist())
    for i in range(5):j=(i+1)%5;f.append([k+i,k+j,k+j+5,k+i+5])
   previous=c.copy()
 o=next(o for o in sc.objects if o.get('public_instance_id')==p['instance_id']);old=o.data;me=bpy.data.meshes.new(old.name+'_parallel');me.from_pydata(v,[],f)
 for mat in old.materials:me.materials.append(mat)
 me.update();o.data=me
# Reuse byte-identical embedded maps without touching their pixels or UVs.
images={};dedup=0
for image in list(bpy.data.images):
 if not image.packed_file:continue
 key=(hashlib.sha256(image.packed_file.data).hexdigest(),image.colorspace_settings.name)
 if key in images:
  canonical=images[key]
  for mat in bpy.data.materials:
   if mat.use_nodes:
    for node in mat.node_tree.nodes:
     if node.type=='TEX_IMAGE' and node.image==image:node.image=canonical;dedup+=1
 else:images[key]=image
for image in list(bpy.data.images):
 if image.users==0:bpy.data.images.remove(image)
(R/'model/public_instances.json').write_text(json.dumps(props,ensure_ascii=False,indent=2));p=json.load(open(R/'model/city_plan.json'));p['urban_areas_v20']['public_furniture']=props
nt=p['urban_areas_v18']['new_town'];boundary=Polygon(nt['polygon']);inside=[r for r in p['real_buildings'] if boundary.covers(Polygon(r['footprint_xy']))];nt['new_source_buildings']=[r['instance_name'] for r in inside];nt['new_source_building_units']=len(inside);nt['existing_residential_lots']=[b['name'] for b in p['buildings'] if b['zone']=='RESIDENTIAL' and boundary.covers(Polygon(b['footprint']))];nt['existing_residential_units']=len(nt['existing_residential_lots']);nt['building_units']=len(inside)+nt['existing_residential_units'];nt['updated_in_version']='v20';p['stats']['new_town_buildings']=nt['building_units'];p['stats']['source_asset_types']=len({b['file'] for b in p['real_buildings']});p['stats']['new_v20_public_instances']=len(props);p['stats']['building_footprint_area_m2']=sum(Polygon(b.get('footprint',b.get('footprint_xy'))).area for b in p['buildings']+p['real_buildings']);p['stats']['building_coverage_percent']=p['stats']['building_footprint_area_m2']/p['stats']['land_area_m2']*100;p['schema']='hero13.city.curved-streets.v20';(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')))
import collections
report=json.load(open(R/'model/build_report.json'));report['public_counts']=dict(collections.Counter(x['type'] for x in props));(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v20.blend'),compress=True);(R/'validation/texture_reuse.json').write_text(json.dumps(dict(policy='Reuse byte-identical packed images; pixels and UVs unchanged; v19 enhanced atlas retained',canonical_images=len(images),image_node_rebindings=dedup),indent=2));print('FINISH_MODEL',len(images),dedup,flush=True)
