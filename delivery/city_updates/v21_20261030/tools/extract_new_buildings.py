"""Extract selected building shells from unused source files, including open models."""
import sys,json,math,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np
from mathutils import Matrix,Vector
from shapely.geometry import MultiPoint
from surface_utils import co,keep_faces
sources=[('S05',R.parent/'reference_models/city (1)(1).glb'),('S07',R.parent/'source_models_v21/city.glb'),('S08',R.parent/'upload/city_street(1).glb'),('S09',R.parent/'source_models_v21/london_city.glb')]
selection={
 'S05':[('Object_6722',0,42,'圆弧商务楼'),('Object_8345',0,40,'折角高层楼'),('Object_6287',2,44,'灰格窗高层楼'),('Object_6014',0,36,'方形商务楼'),('Object_6725',0,34,'曲面办公楼'),('Object_8054',0,32,'玻璃转角楼')],
 'S07':[('Object_4493',1,18,'砖石商住楼'),('Object_4496',0,16,'转角社区楼'),('Object_5285',0,24,'砖红中层楼'),('Object_6017',0,12,'低层街坊楼'),('Object_5534',0,18,'灰色沿街楼'),('Object_3836',2,18,'转折街面楼')],
 'S08':[(None,[-6.81,-.42,-1.99,-2.69,4.03,4.85],20,'红砖屋顶街面楼'),(None,[1.10,-.50,-1.99,5.65,4.45,4.1],20,'浅色正侧立面楼'),(None,[2.20,-8.31,-1.05,6.34,-4.22,3.60],18,'开放楼板施工楼'),('Cube.080_55',None,20,'灰色店铺商住楼')],
 'S09':[('Object_8',5,15,'纵深石墙街面楼'),('Object_14',5,18,'石墙转角商住楼'),('Object_20',4,16,'方形社区楼'),('Object_14',9,14,'低层服务楼'),('Object_14',12,28,'窄体条窗楼'),('Object_32',3,48,'高层退台楼')]
}
catalog=[];evidence=[]
for sid,path in sources:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
 audit=json.load(open(R/'audit'/f'{sid}_geometry.json'));obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];records={o.name:o for o in obs};xyz={o.name:co(o) for o in obs};bounds={n:(a.min(0),a.max(0)) for n,a in xyz.items()};canonical='city_street.glb' if sid=='S08' else path.name;source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
 for ix,(anchor,component,height,zh) in enumerate(selection[sid],1):
  aid=f'{sid}-B{ix:02}';face_map={};excluded=[]
  if sid=='S08' and anchor:
   root=bpy.data.objects[anchor];face_map={o.name:list(range(len(o.data.polygons))) for o in root.children_recursive if o.type=='MESH'};lo=np.min([bounds[n][0] for n in face_map],0);hi=np.max([bounds[n][1] for n in face_map],0);hull=None
  else:
   if anchor:
    component_record=next(x for x in audit['components'] if x['object']==anchor and x['component']==component)
    ao=records[anchor];vertices=np.unique(np.concatenate([ao.data.polygons[fi].vertices[:] for fi in component_record['face_ids']]));pts=xyz[anchor][vertices];lo=pts.min(0);hi=pts.max(0);hull=MultiPoint(pts[:,:2]).convex_hull.buffer(max(hi[:2]-lo[:2])*.012,join_style=2)
    # Only the shell's own spatial footprint is used; retain roof/attachments within it.
    lower=lo[2]-.015;upper=hi[2]+min((hi[2]-lo[2])*.1,.13)
   else:
    lo=np.array(component[:3],float);hi=np.array(component[3:],float);lower=lo[2];upper=hi[2];hull=None
   for o in obs:
    parent=o.parent.name if o.parent else '';bl,bh=bounds[o.name]
    if sid=='S09' and ('Lightmap' in parent or not parent.startswith(('WorldCityBuildings','WorldCityAdvertisements','WorldCityTransparent'))):continue
    if sid in ['S05','S07'] and not parent.startswith('unit_'):continue
    if (bh[:2]<lo[:2]-.02).any() or (bl[:2]>hi[:2]+.02).any() or bh[2]<lower or bl[2]>upper:continue
    arr=xyz[o.name];inside=(arr[:,2]>=lower-1e-7)&(arr[:,2]<=upper+1e-7)
    if hull is not None:
     import shapely
     inside &= shapely.intersects_xy(hull,arr[:,0],arr[:,1])
    else:inside &= (arr[:,:2]>=lo[:2]-1e-6).all(1)&(arr[:,:2]<=hi[:2]+1e-6).all(1)
    faces=[f.index for f in o.data.polygons if all(inside[v] for v in f.vertices)]
    if o.name==anchor:faces=sorted(set(faces)|set(component_record['face_ids']))
    if faces:face_map[o.name]=faces
  parts=[];source_meta=[];decimation=[]
  for name,faces in face_map.items():
   original=records[name];mesh=original.data.copy();mesh.transform(original.matrix_world);mesh.update();part=bpy.data.objects.new(aid+'__'+name,mesh);bpy.context.scene.collection.objects.link(part);face_set=set(faces);keep_faces(part,[i in face_set for i in range(len(mesh.polygons))])
   if part.name not in bpy.context.scene.objects:continue
   source_meta.append(dict(source_mesh=name,source_node=original.parent.name if original.parent else name,face_ids=faces))
   # S08 has highly subdivided flat ornaments and repeated frame detail.
   if sid=='S08' and len(part.data.polygons)>12000:
    bpy.context.view_layer.objects.active=part;mod=part.modifiers.new('V21_Detail_Reduction','DECIMATE');mod.ratio=max(.025,9000/max(1,sum(len(f.vertices)-2 for f in part.data.polygons)));bpy.ops.object.modifier_apply(modifier=mod.name);decimation.append(dict(source_mesh=name,ratio=mod.ratio if False else 'target <= 9000 triangles per detail mesh'))
   parts.append(part)
  assert parts,(aid,anchor)
  points=np.concatenate([co(o) for o in parts]);bottom=points.min(0);top=points.max(0);scale=height/(top[2]-bottom[2]);T=Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation((-(top[0]+bottom[0])/2,-(top[1]+bottom[1])/2,-bottom[2]))
  for part in parts:part.data.transform(T);part.data.update()
  size=((top-bottom)*scale).tolist();placement=size[:];placement[0]=max(placement[0],4);placement[1]=max(placement[1],4)
  edge_counts=collections.Counter();normal_weights=np.zeros(4)
  merged=np.concatenate([co(part) for part in parts]);_,all_ind=np.unique(np.round(merged,5),axis=0,return_inverse=True);offset=0
  for part in parts:
   ind=all_ind[offset:offset+len(part.data.vertices)];offset+=len(part.data.vertices)
   for f in part.data.polygons:
    verts=list(f.vertices)
    for i,v in enumerate(verts):edge_counts[tuple(sorted((int(ind[v]),int(ind[verts[(i+1)%len(verts)]]))))]+=1
    n=f.normal
    if abs(n.z)<.4:
     dots=[n.x,n.y,-n.x,-n.y];normal_weights[int(np.argmax(dots))]+=f.area
  opens=sum(v==1 for v in edge_counts.values());front=[[1,0],[0,1],[-1,0],[0,-1]][int(np.argmax(normal_weights))]
  if sid=='S08':front=[0,-1] if ix!=3 else [0,-1]
  notes='源楼壳存在开放边；保留原状，未补封口，背面/屋顶待后续检查。' if opens else '几何拓扑检查未发现单侧边；内部、底面和可进入性未制作。'
  if sid=='S08' and ix==2:notes='正面和侧面照片立面，背面及屋顶未封口；保留原状。'
  if sid=='S08' and ix==3:notes='开放楼板和外墙框架，部分外墙缺失，未封口；作为施工楼使用。'
  if sid=='S08' and ix==4:notes='保留原有店铺、窗框与屋顶；背面、底面封口未处理，内构件保留。'
  images={n.image for part in parts for m in part.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image};meta=dict(asset_id=aid,source_id=sid,display_name_zh=zh,source_filename=canonical,upload_filename=path.name,source_sha256=source_sha,source_node_name=anchor if anchor else 'spatial_building_selection_'+str(ix),extraction_method='spatial shell-component face selection across source materials; source world transforms baked; UVs retained; no cap geometry added',source_component=component if isinstance(component,int) else None,source_mesh_count=len(parts),uniform_scale=scale,normalized_size_m=size,placement_size_m=placement,source_front=front,building_units=1,file=aid+'.glb',geometry_status='OPEN_SHELL' if opens or sid=='S08' else 'UNCHECKED_INTERIOR',open_boundary_edge_count=opens,issue_note_zh=notes,texture_policy='source UVs and embedded diffuse textures retained; S09 duplicate lightmap overlay excluded',original_texture_sizes=sorted(set(tuple(im.size) for im in images)),low_resolution_texture=any(max(im.size)<=256 for im in images),source_detail_reduction=decimation,added_in_version='v21')
  root=bpy.data.objects.new(aid,None);bpy.context.scene.collection.objects.link(root)
  for k,v in meta.items():
   if isinstance(v,(str,int,float,bool)):root[k]=v
  for part in parts:
   part.parent=root
   for k in ['asset_id','source_id','source_filename','source_sha256','source_node_name','geometry_status','issue_note_zh','added_in_version']:part[k]=meta[k]
   part['source_mesh_name']=part.name.split('__',1)[1]
  bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
  for part in parts:part.select_set(True)
  bpy.context.view_layer.objects.active=root;out=R/'extracted'/meta['file'];bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO')
  meta.update(bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),triangles=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in parts));catalog.append(meta);evidence.append(dict(asset_id=aid,source_filename=canonical,source_sha256=source_sha,selected=source_meta,source_bbox=[bottom.tolist(),top.tolist()],normalization_matrix=[list(row) for row in T],excluded_duplicate_layers='S09 Lightmap meshes; roads, invisible walls, traffic collisions and backdrop sheets are excluded'))
  print('EXTRACTED',aid,zh,[round(x,2) for x in size],meta['triangles'],opens,flush=True)
  for part in parts+[root]:bpy.data.objects.remove(part,do_unlink=True)
 (R/'asset_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2));(R/'audit/extraction_selections.json').write_text(json.dumps(evidence,ensure_ascii=False))
print('EXTRACTION_COMPLETE',len(catalog),flush=True)
