import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'));sys.path.insert(0,str(R/'tools'))
import bpy,numpy as np,shapely
from shapely.geometry import LineString
from city_surface_sampling import HeightField
from surface_utils import co
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('surface_type') in ['terrain','sidewalk'] or o.get('is_site_foundation'))];field=HeightField(obs);p=json.load(open(R/'model/city_plan.json'));cache={}
for w in p['access_v19']:
 line=LineString(w['route']);pts=np.array(shapely.segmentize(line,.75).coords);zz=np.array([field.height(q) for q in pts]);grades=np.abs(np.diff(zz))/np.linalg.norm(np.diff(pts,axis=0),axis=1);j=grades.argmax()
 if grades[j]<.32:continue
 print(w['name'],'MAX',grades[j], 'route length',line.length,'floor',w['floor'],'goal',w['goal_z'],'pts',pts[j:j+2].tolist(),'zz',zz[j:j+2].tolist(),flush=True)
 for q in pts[j:j+2]:
  found=[]
  for o in obs:
   if o.name not in cache:
    x=co(o);cache[o.name]=(x.min(0),x.max(0),None)
   lo,hi,f=cache[o.name]
   if np.all(q>=lo[:2]-.001) and np.all(q<=hi[:2]+.001):
    if f is None:
     try:f=HeightField([o]);cache[o.name]=(lo,hi,f)
     except:continue
    z=f.height(q)
    if z is not None:found.append((o.name,z))
  print('SURFACE',q.tolist(),found,flush=True)
