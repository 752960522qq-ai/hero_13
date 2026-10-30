"""Replace interpolated footprint margins with exact level perimeter aprons."""
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from surface_utils import clip_ground,fingerprint
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v20.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;sites=json.load(open(R/'model/site_levels.json'));cut=unary_union([Polygon(s['poly']).buffer(.3,join_style=2) for s in sites]);changed=[]
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk']:
  h=fingerprint(o);clip_ground(o,cut)
  if o.name in sc.objects and fingerprint(o)!=h:changed.append(o.name)
for s in sites:
 poly=Polygon(s['poly']);ring=poly.buffer(.3,join_style=2).difference(poly.buffer(.02,join_style=2));v=[];f=[]
 for t in shapely.get_parts(shapely.constrained_delaunay_triangles(ring)):
  xy=np.array(t.exterior.coords)[:3]
  if np.linalg.det(np.c_[xy,np.ones(3)])<0:xy=xy[::-1]
  k=len(v);v.extend([[float(x),float(y),s['floor']-.02] for x,y in xy]);f.append([k,k+1,k+2])
 me=bpy.data.meshes.new(s['name']+'_Level_Perimeter');me.from_pydata(v,[],f);me.materials.append(bpy.data.materials['V20_Pavers']);me.update();o=bpy.data.objects.new(s['name']+'_Level_Perimeter',me);sc.collection.objects.link(o);o.parent=bpy.data.objects[f"District_{s['district_id']:02}"];o['district_id']=s['district_id'];o['surface_type']='sidewalk';o['modified_in_version']='v20';o['site_building_margin']=s['name']
report=json.load(open(R/'model/build_report.json'))
for name,h in list(report['unchanged_original_objects'].items()):
 o=sc.objects.get(name)
 if o is not None and fingerprint(o)!=h:
  assert o.get('surface_type') in ['terrain','sidewalk'];del report['unchanged_original_objects'][name];report['changed_original_objects']=sorted(set(report['changed_original_objects'])|{name})
report['level_perimeter_buildings']=len(sites);(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v20.blend'),compress=True);print('LEVEL_PERIMETERS',len(sites),flush=True)
