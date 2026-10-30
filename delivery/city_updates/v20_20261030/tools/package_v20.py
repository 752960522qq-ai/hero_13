from pathlib import Path
import json,csv,shutil,gzip,hashlib,lzma,concurrent.futures
R=Path(__file__).resolve().parents[1];repo=R.parent/'hero_13';out=repo/'delivery/city_updates/v20_20261030';out.mkdir(parents=True,exist_ok=True)
for key in ['native_validation','districts_validation']:assert json.load(open(R/'validation'/f'{key}.json'))['status']=='PASS',key
p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));report=json.load(open(R/'model/build_report.json'));sites=json.load(open(R/'model/site_levels.json'));props=json.load(open(R/'model/public_instances.json'));base=json.load(open(R/'baseline_refs.json'));resolved=json.load(open(R/'districts/districts_manifest.json'));ids=layout['changed_district_ids'];(out/'districts').mkdir(exist_ok=True);(out/'metadata').mkdir(exist_ok=True);(out/'annotations').mkdir(exist_ok=True)
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
counts={d['id']:d['building_units'] for d in base}
for b in layout['removed_placeholder_lots']:counts[district(b['center'])]-=1
for b in sites:counts[b['district_id']]+=1
assert sum(counts.values())==p['stats']['buildings']
def compress(d):
 old=next(x for x in base if x['id']==d);new=next(x for x in resolved['districts'] if x['id']==d);file=R/'districts'/new['file'];data=file.read_bytes();assert hashlib.sha256(data).hexdigest()==new['sha256'];raw=lzma.compress(data,preset=6);parts=[]
 for n,i in enumerate(range(0,len(raw),8*1024*1024)):
  buf=raw[i:i+8*1024*1024];name=f'districts/{file.name}.xz.part{n:03}';(out/name).write_bytes(buf);parts.append(dict(file=name,bytes=len(buf),sha256=hashlib.sha256(buf).hexdigest()))
 return dict(id=d,name=new['name'],file=file.name,bytes=len(data),sha256=new['sha256'],base_sha256=old['sha256'],compression='xz',compressed_bytes=len(raw),compressed_sha256=hashlib.sha256(raw).hexdigest(),parts=parts,building_units_before=old['building_units'],building_units_after=counts[d],change_notes='v20 street-facing building infill, curved streets, offset T junctions, street furniture and continuous graded entrances')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:changed=list(ex.map(compress,ids))
allrows=[];current=[]
for old in base:
 new=next((x for x in changed if x['id']==old['id']),None);allrows.append(dict(id=old['id'],file=old['file'],base_sha256=old['sha256'],sha256=new['sha256'] if new else old['sha256'],changed=new is not None));current.append({**old,'version':'v20','bytes':new['bytes'],'sha256':new['sha256'],'building_units':counts[old['id']],'source':dict(type='incremental_district_parts',manifest='delivery/city_updates/v20_20261030/manifest.json')} if new else old)
manifest=dict(schema='hero13.city.incremental.v20',update_id='v20_20261030',date='2026-10-30',baseline_version='v19',baseline_commit=layout['baseline_commit'],changed_district_ids=ids,unchanged_district_ids=[i for i in range(1,19) if i not in ids],changed_districts=changed,all_districts=allrows,resolved_districts_manifest=resolved,city_building_units=p['stats']['buildings'],oldtown_street_buildings=120,oldtown_rear_buildings=80,new_asset_types_used=len({s['asset_id'] for s in sites}),new_source_instances=len(sites),replaced_placeholder_units=len(layout['removed_placeholder_lots']),new_road_length_m=report['new_road_length_m'],public_furniture_counts=report['public_counts'])
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(repo/'design/city/districts/current_sources_v20.json').write_text(json.dumps(current,ensure_ascii=False,indent=2));(repo/'design/city/districts/districts_manifest.json').write_text(json.dumps(resolved,ensure_ascii=False,indent=2));shutil.copy2(R/'validation/districts_validation.json',repo/'design/city/districts/districts_validation.json')
s=(repo/'delivery/city_updates/v19_20261030/reassemble.py').read_text().replace('v18','v19').replace('v19 set resolved','v20 set resolved');(out/'reassemble.py').write_text(s)
for folder in ['tools','base_tools','validation']:shutil.copytree(R/folder,out/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','diagnose*'))
for src in [R/'layout.json',R/'asset_catalog.json',R/'baseline_refs.json',R/'baseline_districts_manifest.json',R/'model/site_levels.json',R/'model/public_instances.json',R/'model/road_profiles.json',R/'model/build_report.json']:shutil.copy2(src,out/'metadata'/src.name)
(out/'metadata/city_plan.json.gz').write_bytes(gzip.compress((R/'model/city_plan.json').read_bytes(),compresslevel=9,mtime=0))
rows=[]
for b in sites:rows.append(dict(instance_id=b['name'],asset_id=b['asset_id'],name_zh=b['display_name_zh'],source_filename=b['source_filename'],source_node_name=b['source_node_name'],source_sha256=b['source_sha256'],asset_file=b['file'],asset_sha256=b['asset_sha256'],district_id=b['district_id'],layout_group=b['group'],x_m=b['center'][0],y_m=b['center'][1],floor_m=b['floor'],height_m=b['height'],rotation_deg=b['rotation_deg'],uniform_scale=b['scale'],replaces_lots='|'.join(b['replaces'])))
with (out/'annotations/building_instances_v20.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (out/'annotations/public_instances_v20.csv').open('w',encoding='utf-8-sig',newline='') as f:
 names=['instance_id','type','district_id','group','center','z','rotation_deg','scale','start','end','building_count_units'];w=csv.DictWriter(f,fieldnames=names,extrasaction='ignore');w.writeheader();w.writerows(props)
with (out/'annotations/replaced_lots_v20.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['old_lot','replacement_instances']);w.writeheader()
 for old in layout['removed_placeholder_lots']:w.writerow(dict(old_lot=old['name'],replacement_instances='|'.join(b['name'] for b in sites if old['name'] in b['replaces'])))
sources=[]
for name,canonical,sid in [('01-asian_buildings_set.glb','asian_buildings_set.glb','S02'),('city_street(1).glb','city_street.glb','S08')]:
 file=R.parent/'upload'/name;sources.append(dict(upload_name=name,canonical_source=canonical,source_id=sid,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),policy='Byte-identical to the original v19 source; keep source identity and avoid duplicate types.'))
(out/'metadata/supplemental_sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
readme=f'''# 城市 v20：弧线生活街与西岛曲街

基于 v19 `{layout['baseline_commit']}`，只替换 **04、08、09、10** 四个区块，另外 14 块按原 SHA256 沿用。

本轮采用 **{len({s['asset_id'] for s in sites})} 种房屋模型，放入 {len(sites)} 栋**，移除 **{len(layout['removed_placeholder_lots'])} 栋西岛占位楼**。全城从 547 栋变为 **{p['stats']['buildings']} 栋**，净陆地仍为 3.25 km²；老城沿街 120 栋、后巷 80 栋。

## 这次改了什么

- 新城弧线生活街：25 栋商住楼沿弯路改变朝向，采用短段连续街面，支路连接北侧主路。
- 新城商务组团：4 栋高低搭配的建筑，补齐之前备用的两种办公楼型，并建立独立入口步道。
- 西岛曲街：20 栋亚洲商住楼、社区店铺与坡顶住宅替换机械排列的占位楼；S 形街道与错位 T 字支路形成不同尺度街坊。
- 共增加 4 条道路，合计约 {report['new_road_length_m']:.1f} 米，路口接入原有路网，包含人行道、路缘、中心线与斑马线。
- 公共设施：{report['public_counts']}。设施与线路单独计数，不占建筑额度。

重点参考 `city (1)(1).glb`（S05）的弧形主次道路、错位交叉口、街角种植与高低街面关系。按当前地形和已有路口重新建模，参考模型的未封闭背景楼片没有用作近景独立建筑。补传的两个模型与 S02/S08 原文件哈希相同，继续沿用原来源编号。

## 编号和模型来源

建筑沿用 `S02-B01-Ixx` 格式，实例号承接 v19，不重复。每个网格包含来源文件、原节点、楼型、地图实例、所属组团与被替换地块。公共设施使用 `V20-Pxxx`，电线使用 `V20-Cxx`；编号存放在节点属性、CSV 和标注预览中。

- `annotations/building_instances_v20.csv`：本轮逐栋来源、坐标、旋转、缩放与替换关系。
- `annotations/public_instances_v20.csv`：全部公共设施及线路。
- `annotations/replaced_lots_v20.csv`：11 个旧地块的替换对应。
- 房屋素材库继续引用 `../v19_20261030/building_bank/`，本次不重复上传未改素材。贴图沿用原内嵌纹理及 v19 已增强的图集；UV 和像素保持，字节相同的图像共用一份。

## 还原与导入

```bash
python3 reassemble.py --out /new/path/v20_districts
```

分卷、压缩流、最终 GLB 均校验 SHA256。已有完整 v19 区块时可附加 `--baseline-dir /path/to/v19/districts`，在新目录组合成完整 18 块。只移除旧 04/08/09/10 并导入同名新文件；世界坐标单位为米，根位置/旋转为零，缩放为一。

## 验证

原生验证和四个修改区块重新导入均通过，记录见 `validation/`。检查包括来源标注、数量、建筑与道路/邻楼/预留地相交、入口地面连续性、路网连通、道路坡度、线缆净空、公共设施位置、未修改对象几何和 UV 指纹，以及导出坐标误差。分卷还原另有实际校验记录。

交付为静态城市模型。游戏运行时碰撞、导航、交通与目标设备性能尚未在本次接入或测试。
'''
(out/'README.md').write_text(readme)
(out/'REPRODUCE.md').write_text('''# 复现 v20

需要 Blender 4.5.3 LTS，Python 3.11 下的 NumPy、SciPy、Shapely 与 Pillow。将本目录复制为 `work_v20`；仓库位于其同级 `hero_13`。

1. 执行 `tools/restore_baseline.py` 恢复 v19 的当前陆地区块和规划。
2. 在仓库的 v19 目录运行 `restore_building_bank.py --out /path/to/work_v20`，恢复未改动的房屋库。
3. 普通 Python 运行 `tools/plan_v20.py`。规划依赖放入 `deps/`，Blender 依赖放入 `deps311/`；无需重新生成纹理。
4. Blender 后台依次执行 `tools/build_v20.py`、`tools/finish_model.py`、`tools/repair_grades.py`、`tools/finish_walks.py`、`tools/cap_footprints.py`。`finish_model.py` 执行一次，从构建后的原始场景开始；所有 Blender 调用增加 `--python-exit-code 1`。
5. 运行 `tools/validate_v20.py`，通过后执行 `tools/export_verify_v20.py`。导出用的 v19 基准清单取 `metadata/baseline_districts_manifest.json` 放入工作目录根。
6. 渲染 `tools/render_v20.py`；加 `-- before` 获得 v19 对比图。普通 Python 执行 `tools/annotate_v20.py` 和 `tools/package_v20.py`。

来源记录见 `metadata/supplemental_sources.json`，参考分析见 `metadata/reference_layout_notes.md`。编号与图片没有写进建筑贴图。
''')
for path in [repo/'assets/city/README.md',repo/'delivery/city_updates/README.md']:
 text=path.read_text();prefix='> 最新增量为 **v20**：新增 49 栋素材建筑、替换 11 栋西岛占位楼，全城 585 栋；参考 city（1）的道路关系加入弧线生活街、错位支路和公共设施。仅替换 **04/08/09/10**，详见 `delivery/city_updates/v20_20261030/README.md`；当前来源为 `design/city/districts/current_sources_v20.json`。\n\n'
 if not text.startswith('> 最新增量为 **v20**'):path.write_text(prefix+text)
print('PACKED_V20',[(x['id'],x['compressed_bytes'],counts[x['id']]) for x in changed],flush=True)
