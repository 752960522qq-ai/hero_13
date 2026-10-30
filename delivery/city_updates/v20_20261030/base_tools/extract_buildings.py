"""Extract complete source building hierarchies, retaining materials, UVs and provenance."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
import numpy as np
R=Path(__file__).resolve().parents[1];sources=json.load(open(R/'audit/sources.json'))
selection={
 'S02':[(3,'Raohe_terraced_05','亚洲白色沿街楼',18),(157,'Raohe_terraced_04','亚洲绿色沿街楼',16),(409,'Raohe_lowrise_01','亚洲低层商住楼',12),(795,'Raohe_corner','亚洲转角商住楼',16),(1211,'Pitched_roof_house','坡顶双层住宅',8)],
 'S03':[(22,'Stepped_office','阶梯写字楼',64),(32,'Slim_office','窄体写字楼',42),(47,'Twin_office','玻璃写字楼',56),(57,'Dark_office','深色写字楼',52),(194,'Low_office','低层办公楼',27),(207,'Tall_office','高层写字楼',72)],
 'S04':[(3,'Paramount_store','街角百货楼',18),(112,'Service_shops','沿街服务店铺',15),(270,'Corner_shop','转角店铺',14),(443,'Walkup_apartment','多层居民楼',18),(805,'Community_clinic','社区诊所',12),(807,'Local_shop','社区店铺',12),(824,'Slab_apartment','板式公寓',28),(2262,'Laundrette','洗衣店',8),(2334,'Brick_factory','砖墙厂房',17),(2546,'Pawn_shop','双层商铺',13)],
 'S06':[(5,'Soho_cast_iron','铸铁立面街角楼',31),(187,'Soho_brownstone','棕石街面楼',26),(195,'Soho_red_brick','红砖街面楼',24),(202,'Soho_grey','灰色街面楼',24),(208,'Soho_corner','街角多层楼',29),(215,'Soho_shops','低层商业楼',22)]
}
which=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
records=[]
for sid,items in selection.items():
 if which and sid not in which:continue
 src=next(x for x in sources if x['id']==sid);hier=json.load(open(R/'audit'/f'{sid}_hierarchy.json'));nodes={r['index']:r for r in hier['records']}
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R.parent/'upload'/src['file']));bpy.context.view_layer.update()
 for ai,(idx,slug,zh,height) in enumerate(items,1):
  aid=f'{sid}-B{ai:02}';node=nodes[idx];root=bpy.data.objects.get(node['name']);assert root is not None,node['name'];original=[o for o in [root]+list(root.children_recursive) if o.type=='MESH'];parts=[]
  for o in original:
   m=o.data.copy();m.transform(o.matrix_world);m.update();n=bpy.data.objects.new(f'{aid}__{o.name}',m);bpy.context.scene.collection.objects.link(n);parts.append(n)
  xyz=np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in parts]);lo=xyz.min(0);hi=xyz.max(0);s=height/(hi[2]-lo[2]);T=Matrix.Diagonal((s,s,s,1))@Matrix.Translation((-(hi[0]+lo[0])/2,-(hi[1]+lo[1])/2,-lo[2]))
  for o in parts:o.data.transform(T);o.data.update()
  # Connected decorative pieces, shop signs and roof equipment stay with their building.
  meta=dict(asset_id=aid,display_name_zh=zh,source_id=sid,source_filename=src['file'],source_sha256=src['sha256'],source_node_index=idx,source_node_name=node['name'],extraction_method='complete named hierarchy; world transforms baked; uniform scale; bottom-center origin',uniform_scale=s,normalized_size_m=[float((hi[0]-lo[0])*s),float((hi[1]-lo[1])*s),height],building_units=1,source_mesh_count=len(parts),file=f'{aid}_{slug}.glb',texture_policy='original embedded pixels; no invented details',status='candidate_not_yet_placed')
  rootnew=bpy.data.objects.new(aid,None);bpy.context.scene.collection.objects.link(rootnew)
  for k,v in meta.items():
   if isinstance(v,(str,int,float)):rootnew[k]=v
  for o in parts:
   o.parent=rootnew;o['asset_id']=aid;o['source_id']=sid;o['source_filename']=src['file'];o['source_node_index']=idx;o['source_mesh_name']=o.name.split('__',1)[1]
  bpy.ops.object.select_all(action='DESELECT');rootnew.select_set(True)
  for o in parts:o.select_set(True)
  bpy.context.view_layer.objects.active=rootnew
  out=R/'extracted'/meta['file'];bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO')
  meta['bytes']=out.stat().st_size;meta['sha256']=hashlib.sha256(out.read_bytes()).hexdigest();meta['triangles']=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in parts);meta['images']=[dict(name=im.name,size=list(im.size)) for im in {n.image for o in parts for m in o.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}];records.append(meta)
  for o in parts+[rootnew]:bpy.data.objects.remove(o,do_unlink=True)
  print('EXTRACTED',aid,meta['file'],meta['normalized_size_m'],flush=True)
 (R/'audit'/f'{sid}_extracted.json').write_text(json.dumps([x for x in records if x['source_id']==sid],ensure_ascii=False,indent=2))
records=[]
for p in sorted((R/'audit').glob('S??_extracted.json')):records.extend(json.load(open(p)))
(R/'asset_catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print('CATALOG',len(records),flush=True)
