"""Add the supplied shop pair and back-lane apartments to the saved metric city.

Run with Blender 4.5.3: --source CITY --uploads UPLOADS --out OUT --deps DEPS.
The existing road/bridge meshes and eleven source buildings stay in world space.
"""
import argparse,sys,json,math,hashlib,shutil
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Matrix
ap=argparse.ArgumentParser()
for k in ['source','uploads','out','deps']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).parent))
from compact_city_math import *
from shapely.geometry import box
a.out.mkdir(parents=True,exist_ok=True);p=json.loads((a.source/'city_plan.json').read_text());baseline=json.loads(json.dumps(p));oldp=p['buildings']
if p.get('oldtown_four'):raise SystemExit('This city already includes the four assets; edit the saved v9 blend directly, or run this script with a v8 source.')
bpy.ops.wm.open_mainfile(filepath=str((a.source/'huizhou_road_network.blend').resolve()));sc=bpy.context.scene
groups={o.name:o for o in sc.objects if o.type=='EMPTY'};root=groups['Huizhou_Reconstructed_City_5p8km2'];root['version']='v9_oldtown_four';root['description']='v8 city plus joined shopfronts 12/13 and back-lane apartments 13/14.'
islands={k:Polygon(v) for k,v in p['coasts'].items()};lake=Polygon(p['lake']);gp=SurfaceProjector([e for e in p['edges'] if e['layer'].startswith('GROUND')]);groundz=lambda xy:terrain_height(xy,islands,lake,gp)
concrete=bpy.data.materials['Bridge_Concrete'];roadmat=bpy.data.materials['Road_Modular_Original_Atlas'];seammat=bpy.data.materials['Oldtown_Seam_Plaster']
def mesh(name,v,f,material,parent,uv=None):
 m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(material);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=parent
 if uv is not None:m.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uv,np.float32)[np.asarray(f)].ravel())
 return o
def prism(name,poly,top,bottom,material=concrete):
 xy=np.asarray(shapely.orient_polygons(poly).exterior.coords)[:-1];n=len(xy);v=np.vstack([np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]]);f=[]
 for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
 return mesh(name,v.tolist(),f,material,groups['08_BUILDING_FOOTINGS'])
new=[]
specs=[('04-storefront-12.glb','storefront_12.glb','OLDTOWN_Joined_Storefront_12',13.2,math.pi),('03-urban-shopfront-13.glb','urban_shopfront_13.glb','OLDTOWN_Joined_Urban_Shopfront_13',13.2,math.pi),('02-old-apartment-building-3d-model-13.glb','old_apartment_13.glb','OLDTOWN_Backlane_Apartment_13',16.0,0),('01-apartment-building-3d-model-14.glb','apartment_14.glb','OLDTOWN_Backlane_Apartment_14',16.4,0)]
lane={'name':'MAIN_OLD_ALLEY_120_BACKLANE','points':[[194.94,260.0],[343.56,260.0]],'width':3.6};aa,bb=np.array(lane['points']);L=float(np.linalg.norm(bb-aa));heights=gp.height([aa,bb])+.143577;lane.update(end_heights=heights.tolist(),length=L,max_grade=float(abs(heights[1]-heights[0])/L));p['pedestrian_alleys'].append(lane)
cursor=338.;backcursor=214.
for upload,filename,name,height,theta in specs:
 source=a.uploads/upload;dest=a.source/'buildings'/filename;shutil.copy2(source,dest);before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update();imported=set(sc.objects)-before;parts=[o for o in imported if o.type=='MESH'];co=np.concatenate([np.array([o.matrix_world@v.co for v in o.data.vertices]) for o in parts]);lo=co.min(0);hi=co.max(0);sourceheight=hi[2]-lo[2];s=height/sourceheight
 floorvotes=[]
 for o in parts:
  o.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in o.data.loop_triangles]);v=np.array([o.matrix_world@v.co for v in o.data.vertices])[tri];nn=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);cz=v[:,:,2].mean(1);mask=(nn[:,2]>0)&(cz<lo[2]+.15*sourceheight);bins=np.round((cz[mask]-lo[2])/(sourceheight*.001)).astype(int);freq=np.bincount(bins,weights=nn[mask,2]);winner=freq.argmax();floorvotes.append(float(np.average(cz[mask][bins==winner],weights=nn[mask,2][bins==winner])))
 floorref=float(np.mean(floorvotes));mask=(co[:,2]>lo[2]+sourceheight*.18)&(co[:,2]<lo[2]+sourceheight*.75);core=co[mask];left,right=np.quantile(core[:,0],[.002,.998])*s;front=float(np.quantile(core[:,1],.008)*s);width=float(right-left)
 shop='Joined_' in name
 if shop:anchor=np.array([cursor,222.475]);cursor-=width-.02;floor=7.359764250529281
 else:anchor=np.array([backcursor,261.825]);backcursor+=width+1.2;floor=float(np.interp(anchor[0]+width/2,[aa[0],bb[0]],heights)+.006)
 R=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]]);rect=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])*s;xy=(rect-[left,front])@R.T+anchor;poly=Polygon(xy);pad=poly.buffer(.10,join_style=2)
 inst=bpy.data.objects.new(name,None);sc.collection.objects.link(inst);inst.parent=groups['07_SOURCE_BUILDINGS'];inst.matrix_world=Matrix.Translation((*anchor,floor-.008))@Matrix.Rotation(theta,4,'Z')@Matrix.Translation((-left,-front,0))@Matrix.Diagonal((s,s,s,1))@Matrix.Translation((0,0,-floorref))
 for o in imported:
  if o.parent not in imported:old=o.matrix_world.copy();o.parent=inst;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=old
 for i,o in enumerate(parts):o.name=name+f'_Source_Mesh_{i:02d}';o['source_filename']=filename
 inst['is_building_instance']=True;inst['source_filename']=filename;inst['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();inst['target_height_m']=height;inst['corner_turn_degrees']=0.;inst['direct_sidewalk_frontage']=shop;inst['direct_alley_frontage']=not shop
 bottom=float(min(groundz(np.asarray(pad.exterior.coords)).min(),floor)-.45);prism(name+'_Foundation',pad,floor-.018,bottom)
 r={'instance_name':name,'file':filename,'source_filename':filename,'uniform_scale':float(s),'local_axis_scale':[1.,1.,1.],'target_height_m':height,'source_bounds':[lo.tolist(),hi.tolist()],'source_floor_reference':floorref,'turn':0.,'left':float(left),'right':float(right),'front':front,'rotated_xy_bounds':[(lo[:2]*s).tolist(),(hi[:2]*s).tolist()],'anchor':anchor.tolist(),'theta':theta,'angle':theta,'center':list(poly.centroid.coords[0]),'region':'MAIN','footprint_xy':xy.tolist(),'pad_xy':list(pad.exterior.coords),'floor':floor,'foundation_bottom_m':bottom,'direct_sidewalk_frontage':shop,'direct_alley_frontage':not shop,'access_alley':None if shop else lane['name'],'addition_revision':'v9_oldtown_four'};new.append(r)
p['real_buildings'].extend(new)
# Remove occupied placeholder lots and clear the connected rear passage, then remap lot IDs.
lanecut=LineString(lane['points']).buffer(lane['width']/2+.14,cap_style=2);reserved=unary_union([lanecut,*[Polygon(r['pad_xy']).buffer(.25,join_style=2) for r in new]]);removed=[i for i,b in enumerate(oldp) if Polygon(b['footprint']).intersects(reserved)];keep=[i for i in range(len(oldp)) if i not in set(removed)];mapping={old:i for i,old in enumerate(keep)}
for o in list(sc.objects):
 if o.type!='MESH' or not o.data.attributes.get('source_building_index'):continue
 bm=bmesh.new();bm.from_mesh(o.data);layer=bm.faces.layers.int['source_building_index'];drop=[f for f in bm.faces if f[layer] in removed];bmesh.ops.delete(bm,geom=drop,context='FACES');unused=[v for v in bm.verts if not v.link_faces];bmesh.ops.delete(bm,geom=unused,context='VERTS')
 for f in bm.faces:f[layer]=mapping[f[layer]]
 if not bm.faces:bm.free();bpy.data.objects.remove(o,do_unlink=True);continue
 bm.to_mesh(o.data);bm.free();o.data.update();ids=[x.value for x in o.data.attributes['source_building_index'].data];o['placeholder_lot_count']=len(set(ids))
p['buildings']=[oldp[i] for i in keep]
# Cut only the new sites and lane from the original triangulated terrain. Preserve colors.
cut=unary_union([LineString(lane['points']).buffer(lane['width']/2+.03,cap_style=2),*[Polygon(r['pad_xy']) for r in new]])
for o in list(sc.objects):
 if o.type!='MESH' or o.get('surface_type')!='terrain':continue
 m=o.data;v=np.array([x.co[:] for x in m.vertices]);m.calc_loop_triangles();faces=np.array([t.vertices[:] for t in m.loop_triangles]);tris=v[faces];poly=shapely.polygons(tris[:,:,:2]);touch=shapely.intersects(poly,cut)
 if not touch.any():continue
 kept=tris[~touch];made=[]
 for tri,part in zip(tris[touch],poly[touch]):
  diff=part.difference(cut)
  if diff.is_empty:continue
  for t in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
   if t.geom_type!='Polygon' or t.area<1e-10:continue
   xy=np.asarray(t.exterior.coords)[:3];q=tri[:,:2];basis=np.c_[q,np.ones(3)];z=np.c_[xy,np.ones(3)]@np.linalg.solve(basis,tri[:,2]);made.append(np.c_[xy,z])
 out=np.concatenate([kept,np.asarray(made).reshape(-1,3,3)]);det=np.cross(out[:,1]-out[:,0],out[:,2]-out[:,0])[:,2];out[det<0]=out[det<0,::-1];oldmat=list(m.materials);nm=bpy.data.meshes.new(m.name+'_v9_sites');nm.from_pydata(out.reshape(-1,3),[],np.arange(out.size//3).reshape(-1,3));nm.materials.append(oldmat[0]);col=nm.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT');col.data.foreach_set('color',np.tile([.52,.48,.38,1],(len(nm.vertices),1)).astype(np.float32).ravel());nm.update();o.data=nm
# Original sidewalk-atlas walkway and retaining bed.
v=[];f=[];uv=[];stations=np.unique(np.r_[np.arange(0,L,1.8),L])
for t in stations:
 c=aa+(bb-aa)*t/L;z=np.interp(t,[0,L],heights);v.extend([[c[0],c[1]-1.8,z],[c[0],c[1]+1.8,z]]);uv.extend([[.271,.7766-.1777*(t%16.9048)/16.9048],[.216,.7766-.1777*(t%16.9048)/16.9048]])
for i in range(len(stations)-1):j=2*i;f.extend([[j,j+2,j+3],[j,j+3,j+1]])
o=mesh(lane['name'],v,f,roadmat,groups['10_PEDESTRIAN_NETWORK'],uv);o['surface_type']='pedestrian';o['maximum_grade']=lane['max_grade'];sidev=[];sidef=[]
boundary=np.asarray(shapely.segmentize(LineString([aa,bb]).buffer(1.8,cap_style=2),max_segment_length=2).exterior.coords)
for q0,q1 in zip(boundary[:-1],boundary[1:]):
 xy=np.array([q0,q1]);top=np.interp(xy[:,0],[aa[0],bb[0]],heights);soil=groundz(xy);lower=np.minimum(soil-.2,top-.22);upper=np.maximum(soil-.035,top-.015);j=len(sidev);sidev.extend([[*q0,lower[0]],[*q1,lower[1]],[*q1,upper[1]],[*q0,upper[0]]]);sidef.extend([[j,j+1,j+2],[j,j+2,j+3]])
mesh(lane['name']+'_Cut_Fill_Bed',sidev,sidef,concrete,groups['10_PEDESTRIAN_NETWORK'])
# A narrow solid party wall closes the shared model edge; it is not a roof canopy.
l,r=new[:2];joint=float(r['anchor'][0]);y0=max(Polygon(l['footprint_xy']).bounds[1],Polygon(r['footprint_xy']).bounds[1]);y1=min(Polygon(l['footprint_xy']).bounds[3],Polygon(r['footprint_xy']).bounds[3]);prism('Oldtown_Joined_12_13_Partywall',box(joint-.075,y0+.07,joint+.075,y1-.07),min(q['floor']+q['target_height_m'] for q in [l,r])-.65,l['floor']-.15,seammat)
land=unary_union(list(islands.values())).difference(lake);oldwindow=box(-680,60,740,620).intersection(land);coverage=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),pedestrian_alleys=len(p['pedestrian_alleys']),building_coverage_percent=100*coverage.area/land.area,oldtown_coverage_percent=100*coverage.intersection(oldwindow).area/oldwindow.area)
p['oldtown_four']={'schema':'hero13.city.oldtown-four.v9','joined_shopfronts':[r['instance_name'] for r in new[:2]],'backlane_apartments':[r['instance_name'] for r in new[2:]],'new_alley':lane['name'],'removed_placeholders':[oldp[i]['name'] for i in removed],'road_network_changed':False};report={'new_buildings':new,'new_alley':lane,'removed_placeholder_indices':removed,'removed_placeholder_names':p['oldtown_four']['removed_placeholders'],'stats':p['stats'],'baseline_existing_source_instances':len(baseline['real_buildings'])}
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
bpy.context.view_layer.update();(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'oldtown_four_build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'huizhou_road_network.blend').resolve()),compress=True);bpy.ops.export_scene.gltf(filepath=str((a.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO');print('OLDTOWN_FOUR_SAVED',json.dumps(p['oldtown_four']),flush=True)
