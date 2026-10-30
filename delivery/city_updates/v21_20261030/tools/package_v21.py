"""Package four changed districts and the 22 single-use source models."""
from pathlib import Path
import json,csv,shutil,gzip,hashlib,lzma,tarfile,io,collections,concurrent.futures
R=Path(__file__).resolve().parents[1];repo=R.parent/'hero_13';out=repo/'delivery/city_updates/v21_20261030';out.mkdir(parents=True,exist_ok=True)
for key in ['native_validation','districts_validation']:assert json.load(open(R/'validation'/f'{key}.json'))['status']=='PASS',key
p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));report=json.load(open(R/'model/build_report.json'));sites=json.load(open(R/'model/site_levels.json'));cat=json.load(open(R/'asset_catalog.json'));base=json.load(open(R/'baseline_refs.json'));resolved=json.load(open(R/'districts/districts_manifest.json'));ids=layout['changed_district_ids']
for name in ['districts','metadata','annotations','building_bank','previews','textures']:(out/name).mkdir(exist_ok=True)
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
counts={d['id']:d['building_units'] for d in base}
for b in layout['removed_placeholder_lots']:counts[district(b['center'])]-=1
for b in sites:counts[b['district_id']]+=1
assert sum(counts.values())==p['stats']['buildings']
def parts(raw,prefix):
 records=[]
 for n,i in enumerate(range(0,len(raw),8*1024*1024)):
  data=raw[i:i+8*1024*1024];file=prefix+f'.part{n:03}';(out/file).write_bytes(data);records.append(dict(file=file,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 return records
def compress(d):
 old=next(x for x in base if x['id']==d);new=next(x for x in resolved['districts'] if x['id']==d);file=R/'districts'/new['file'];data=file.read_bytes();assert hashlib.sha256(data).hexdigest()==new['sha256'];raw=lzma.compress(data,preset=6)
 return dict(id=d,name=new['name'],file=file.name,bytes=len(data),sha256=new['sha256'],base_sha256=old['sha256'],compression='xz',compressed_bytes=len(raw),compressed_sha256=hashlib.sha256(raw).hexdigest(),parts=parts(raw,'districts/'+file.name+'.xz'),building_units_before=old['building_units'],building_units_after=counts[d],change_notes='v21: newly mined S05/S07/S08/S09 buildings, exactly one instance per model; open geometry explicitly labeled; graded entrances')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:changed=list(ex.map(compress,ids))
allrows=[];current=[]
for old in base:
 new=next((x for x in changed if x['id']==old['id']),None);allrows.append(dict(id=old['id'],file=old['file'],base_sha256=old['sha256'],sha256=new['sha256'] if new else old['sha256'],changed=new is not None));current.append({**old,'version':'v21','bytes':new['bytes'],'sha256':new['sha256'],'building_units':counts[old['id']],'source':dict(type='incremental_district_parts',manifest='delivery/city_updates/v21_20261030/manifest.json')} if new else old)
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w') as tar:
 for a in cat:tar.add(R/'extracted'/a['file'],arcname='extracted/'+a['file'])
 tar.add(R/'asset_catalog.json',arcname='asset_catalog.json')
raw=lzma.compress(buf.getvalue(),preset=6);bank=dict(file='building_bank_v21.tar.xz',compression='xz',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),parts=parts(raw,'building_bank/building_bank_v21.tar.xz'),asset_count=len(cat),maximum_map_instances_per_asset=1)
manifest=dict(schema='hero13.city.incremental.v21',update_id='v21_20261030',date='2026-10-30',baseline_version='v20',baseline_commit=layout['baseline_commit'],changed_district_ids=ids,unchanged_district_ids=[i for i in range(1,19) if i not in ids],changed_districts=changed,all_districts=allrows,resolved_districts_manifest=resolved,city_building_units=p['stats']['buildings'],oldtown_street_buildings=120,oldtown_rear_buildings=80,new_asset_types_used=len(cat),new_source_instances=len(sites),maximum_instances_per_new_asset=1,instances_by_source=report['instances_by_source'],replaced_placeholder_units=len(layout['removed_placeholder_lots']),building_bank=bank,known_open_geometry_policy='Open backs, missing roofs and incomplete facade shells retained and annotated, as requested.')
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(repo/'design/city/districts/current_sources_v21.json').write_text(json.dumps(current,ensure_ascii=False,indent=2));(repo/'design/city/districts/districts_manifest.json').write_text(json.dumps(resolved,ensure_ascii=False,indent=2));shutil.copy2(R/'validation/districts_validation.json',repo/'design/city/districts/districts_validation.json')
s=(repo/'delivery/city_updates/v20_20261030/reassemble.py').read_text().replace('v20','__NEWVERSION__').replace('v19','v20').replace('__NEWVERSION__','v21');(out/'reassemble.py').write_text(s)
restore='''from pathlib import Path
import json,lzma,hashlib,tarfile,io,argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=Path(__file__).resolve().parent;m=json.load(open(root/'manifest.json'))['building_bank'];data=bytearray()
for part in m['parts']:
 b=(root/part['file']).read_bytes();assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];data.extend(b)
assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256'];a.out.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(lzma.decompress(data))) as tar:tar.extractall(a.out,filter='data')
print('Restored',m['asset_count'],'building models; maximum one map instance per model.')
'''
(out/'restore_building_bank.py').write_text(restore)
for folder in ['tools','base_tools','validation']:shutil.copytree(R/folder,out/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','diagnose*'))
for src in [R/'layout.json',R/'asset_catalog.json',R/'baseline_refs.json',R/'baseline_districts_manifest.json',R/'model/site_levels.json',R/'model/build_report.json',R/'model/entrances.json',R/'audit/texture_enhancement_prompt.txt']:shutil.copy2(src,out/'metadata'/src.name)
(out/'metadata/city_plan.json.gz').write_bytes(gzip.compress((R/'model/city_plan.json').read_bytes(),compresslevel=9,mtime=0));(out/'metadata/extraction_selections.json.gz').write_bytes(gzip.compress((R/'audit/extraction_selections.json').read_bytes(),compresslevel=9,mtime=0))
shutil.copy2(R/'textures/S09_city_facades_enhanced.png',out/'textures/S09_city_facades_enhanced.png');shutil.copy2(R/'audit/source_WorldCityBuildings2.png',out/'textures/S09_city_facades_original.png')
source_rows=[]
for sid in ['S05','S07','S08','S09']:
 a=json.load(open(R/'audit'/f'{sid}_geometry.json'));source_rows.append(dict(source_id=sid,filename=a['file'],sha256=a['sha256'],adopted_assets=[c['asset_id'] for c in cat if c['source_id']==sid],adopted_asset_count=sum(c['source_id']==sid for c in cat),maximum_instances_per_asset=1))
(out/'metadata/source_inputs.json').write_text(json.dumps(source_rows,ensure_ascii=False,indent=2))
def csvfile(name,rows):
 with (out/'annotations'/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
rows=[]
for b in sites:
 a=next(a for a in cat if a['asset_id']==b['asset_id']);rows.append(dict(instance_id=b['name'],asset_id=b['asset_id'],name_zh=a['display_name_zh'],source_filename=b['source_filename'],source_node_name=b['source_node_name'],source_sha256=b['source_sha256'],asset_file=b['file'],asset_sha256=b['asset_sha256'],district_id=b['district_id'],layout_group=b['group'],x_m=b['center'][0],y_m=b['center'][1],floor_m=b['floor'],height_m=b['height'],rotation_deg=b['rotation_deg'],uniform_scale=b['scale'],map_instances_of_this_asset=1,maximum_instances_per_asset=1,quality_label_zh=a['quality_label_zh'],issue_note_zh=a['issue_note_zh'],texture_enhanced=a.get('texture_enhanced',False),replaces_lots='|'.join(b['replaces'])))
csvfile('building_instances_v21.csv',rows);csvfile('model_quality_labels.csv',[dict(asset_id=a['asset_id'],name_zh=a['display_name_zh'],source_filename=a['source_filename'],quality_label_zh=a['quality_label_zh'],issue_note_zh=a['issue_note_zh'],open_boundary_edges=a['open_boundary_edge_count'],map_instance_count=1,texture_enhanced=a.get('texture_enhanced',False)) for a in cat]);csvfile('replaced_lots_v21.csv',[dict(old_lot=b['name'],replacement_instances='|'.join(s['name'] for s in sites if b['name'] in s['replaces'])) for b in layout['removed_placeholder_lots']])
if (R/'previews/final').exists():shutil.copytree(R/'previews/final',out/'previews',dirs_exist_ok=True)
readme=f'''# 城市 v21：其他来源楼型，一款一栋

基于 v20 `{layout['baseline_commit']}`，只更新 **04、08、09、10**，其他 14 块保留原 SHA256。

本轮从此前未采用的 4 个来源文件提取 **22 款建筑，各放 1 栋**，替换 **{len(layout['removed_placeholder_lots'])} 栋占位楼**，全城 **{p['stats']['buildings']} 栋**。新城 12 栋，西岛 10 栋。没有复用这批新楼型；后续接入请遵守每款最多一个地图实例。

| 来源 | 模型编号 | 数量 |
|---|---|---:|
| city (1)(1).glb | S05-B01～B06 | 6 |
| city.glb | S07-B01～B06 | 6 |
| city_street.glb / 补传 city_street(1).glb | S08-B01～B04 | 4 |
| london_city.glb | S09-B01～B06 | 6 |

## 模型标注

按用户要求保留未封口模型：单面/正侧立面、缺背面/屋顶和开放楼板均可纳入，问题没有作为筛除条件。建筑保留原有缺口；场地地坪不作为建筑封口。每款的实际情况写入网格属性、`annotations/model_quality_labels.csv` 和标注预览。S08-B03 为开放楼板施工楼；S08-B04 为灰色店铺商住楼。

建筑采用 `Sxx-Bxx-I01`；本轮不存在 I02。来源文件、原始部件、SHA256、地图坐标、缩放、地坪高度、替换地块均在 `annotations/building_instances_v21.csv`。精确源面选择与归一化矩阵见 `metadata/extraction_selections.json.gz`。

## 布局和贴图

新城道路沿线补入不同轮廓的高楼、街面楼与施工楼；西岛采用转角和短段街面，保留已有弧线道路与公共设施。沿用 v20 地图路网，不改 CBD、老城 120 栋沿街楼和 80 栋后巷楼、天明大厦预留地。

S09 六款共享外墙图集经过图像编辑增强，实际由 **1024×1024 提升到 1254×1254**；没有将其标为 2K。原图和增强图在 `textures/`，提示词在 `metadata/texture_enhancement_prompt.txt`，使用内置图像生成编辑。图集区域位置经目视核对，新增细节属于 AI 解释。替换仅涉及图像字节，几何和 UV 访问器字节保持一致，见 `validation/texture_enhancement.json`。其余保留原贴图，S08 的高密度装饰部件做了减面。

## 还原

```bash
python3 reassemble.py --out /new/path/v21_districts
python3 restore_building_bank.py --out /new/path/v21_bank
```

第一条命令还原四个修改后的 GLB；配合 `--baseline-dir /path/to/v20/districts` 可在新目录组合完整 18 块。第二条还原这批 22 款独立 GLB。分卷最大 8 MiB，分卷、压缩流和 GLB 均检查 SHA256。单位为米，世界坐标不变。

## 验证与限制

原生场景检查、每款一次约束、全部来源标注、建筑与道路/邻楼/预留地相交、入口和周边地面连续性、旧建筑/路网保留检查均通过；四区块导出后重导入检查通过。实际分卷还原结果见 `validation/reassembly_validation.json`。

交付为静态城市模型。未封口情况保留并标注，运行时碰撞、导航、交通和目标设备性能未在本次接入或测试。
'''
(out/'README.md').write_text(readme)
(out/'REPRODUCE.md').write_text('''# 复现 v21

使用 Blender 4.5.3 LTS、Python 3.11 的 NumPy/SciPy/Shapely/Pillow。工具根目录命名为 work_v21，与 hero_13 同级。

1. 运行 tools/restore_baseline.py 还原 v20 区块与规划；deps 和 deps311 分别提供系统 Python 和 Blender Python 依赖。
2. 四个原始 GLB 按 metadata/source_inputs.json 的 SHA256 准备。audit_new_sources.py 检查源文件；extract_new_buildings.py 提取。若仅恢复资产库，直接运行 restore_building_bank.py。
3. textures/S09_city_facades_enhanced.png 放入工作目录 textures，原始图放入 audit/source_WorldCityBuildings2.png；从原始文件重新提取时运行 apply_source_enhancement.py，直接还原建筑库时跳过（已包含增强贴图）。增强使用内置图像编辑，保存了原图、增强图、提示词和实际尺寸。
4. 运行 plan_v21.py。22 款每款只能出现一次，这一约束同时在规划、模型属性与验证中检查。
5. Blender 后台运行 build_v21.py、validate_v21.py；每次调用使用 --python-exit-code 1。构建优先读取缓存的 v20 原生场景，没有缓存时导入四个 v20 GLB。
6. 验证通过后运行 export_verify_v21.py。渲染 render_v21.py，附加 -- before 渲染 v20 对比；render_asset_gallery.py 生成素材预览；annotate_v21.py 生成标注图，package_v21.py 打包。

构建不会修补源楼体缺口；仅增加场地地坪、入口和来源标注。每栋楼的选择面和归一化矩阵在 metadata/extraction_selections.json.gz。
''')
prefix=f'> 最新增量为 **v21**：从另外 4 个来源提取 22 款房屋，每款仅放一栋；替换 3 栋占位楼，全城 {p["stats"]["buildings"]} 栋。未封口模型已标注。仅更新 **04/08/09/10**，详见 `delivery/city_updates/v21_20261030/README.md`；当前来源为 `design/city/districts/current_sources_v21.json`。\n\n'
for file in [repo/'assets/city/README.md',repo/'delivery/city_updates/README.md',repo/'design/city/districts/README.md']:
 text=file.read_text()
 if not text.startswith('> 最新增量为 **v21**'):file.write_text(prefix+text)
print('PACKAGED_V21',[(c['id'],c['compressed_bytes'],counts[c['id']]) for c in changed],bank['bytes'],flush=True)
