"""Package validated native source, independently checked district models and previews."""
import argparse,csv,gzip,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
ap=argparse.ArgumentParser()
for k in ['repo','source','model','plan','previews','districts','meshes','descriptors','out']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args();v=json.loads((a.model/'compact_validation.json').read_text());dv=json.loads((a.districts/'districts_validation.json').read_text());assert v['status']=='PASS' and dv['validation_passed'];p=json.loads(a.plan.read_text());stats=p['stats'];manifest=json.loads((a.districts/'districts_manifest.json').read_text());a.out.mkdir(parents=True,exist_ok=True)
assert all((a.previews/f).is_file() for f in ['01_city_overview.png','02_cbd_interchange.png','03_oldtown_frontage.png','04_east_flyover.png','05_underpass.png','compact_city_plan.png'])
total_mb=sum(d['file_size_bytes'] for d in manifest['districts'])/1e6;largest=max(d['file_size_bytes'] for d in manifest['districts'])/1e6
data=a.repo/'design/city';data.mkdir(parents=True,exist_ok=True);compact=data/'compact';compact.mkdir(exist_ok=True)
sourcecity=a.source/'design/city';oldplan=sourcecity/'city_plan.json'
before=data/'city_plan_before_compact.json.gz'
if not before.exists():before.write_bytes(gzip.compress(oldplan.read_bytes(),mtime=0))
(data/'city_plan.json.gz').write_bytes(gzip.compress(a.plan.read_bytes(),mtime=0))
for src in [a.model/'compact_validation.json',a.model/'compact_build_report.json',a.meshes/'mesh_report.json',a.plan.parent/'compact_plan_summary.json']:
    shutil.copy2(src,compact/src.name)
shutil.copy2(a.descriptors,compact/'source_descriptors.json');(compact/'massing_manifest.json.gz').write_bytes(gzip.compress((a.model/'massing_manifest.json').read_bytes(),mtime=0));(compact/'playable_boundary.geojson.gz').write_bytes(gzip.compress((a.plan.parent/'playable_boundary.geojson').read_bytes(),mtime=0))
history=a.repo/'assets/city/README_history_v7.md'
if not history.exists():history.write_bytes(subprocess.run(['git','-C',str(a.repo),'show','HEAD:assets/city/README.md'],check=True,capture_output=True).stdout)
clearances='、'.join(f"{q['name']}：{q['minimum_actual_clearance_m']:.2f} m" for q in v['interchanges'])
report=f'''# 5.8 km² 城市重构交付说明

本次重新绘制三岛岸线、街道拓扑和建筑地块，没有整体缩小旧场景。保留 11 个原建筑素材各一栋，原有米制高度和贴图；其他建筑继续使用方块体量。局部道路找平、坡道入口和挡土适配围绕新路网重新生成。

| 项目 | 本次结果 |
| --- | --- |
| 净陆地可玩区边界面积 | {stats['land_area_m2']/1e6:.2f} km² |
| 加入跨水桥面后的平面区域面积 | {stats['land_plus_bridge_play_area_m2']/1e6:.4f} km² |
| 主岛／西岛净陆地／东岛 | 3.55／1.12／1.13 km² |
| 道路中心线总长 | {stats['road_length_m']/1000:.2f} km |
| 道路边／拓扑节点 | {stats['road_edges']}／{stats['junctions']} |
| 道路连通分量 | 1 |
| 新步行街巷 | {stats['pedestrian_alleys']} 条，宽 3.6 m |
| 立交及连接匝道 | 2 处／6 条 |
| 最大道路中心线纵坡 | {stats['max_grade']*100:.2f}% |
| 地形标高范围 | {v['terrain_height_range_m'][0]:.2f}–{v['terrain_height_range_m'][1]:.2f} m |
| 素材建筑／占位地块 | 11／{stats['placeholder_lots']} |
| 全城建筑占地覆盖率／新老城片区覆盖率 | {stats['building_coverage_percent']:.1f}%／{stats['oldtown_coverage_percent']:.1f}% |
| 完整 GLB | {v['file_size_bytes']/1e6:.2f} MB（十进制） |
| 18 个区块 GLB 合计／最大单块 | {total_mb:.2f}／{largest:.2f} MB |

面积按三岛陆地边界扣除湖面计算；海水、湖水不计入。桥面只计算跨水部分，城市立交的上下层不重复增加平面面积。建筑地块属于陆地可玩区边界内，边界面积与游戏导航网格的可行走面积是不同的度量。

老城采用小街坊、沿街连续低层占位和后排院落；CBD 采用裙房与塔楼；外围住宅、大学、市政文化、西岛村镇及东岛工业形成密度和高度层次。六栋原店面总长约 127.02 m，沿现有人行道留约 2.5 cm 收边缝；这段道路局部找平。拐角楼在右端，旋转 90°，原深度方向 1.45 倍适配保留，没有镜像或新增连续雨顶棚。两栋 CBD 素材楼通过顺坡入口广场与人行道连接。

重新导入完整 GLB 后，完成 {v['road_surface_samples']:,} 处道路表面采样、119 条街巷连续性、入口接缝与 {v['pedestrian_headroom_rays']:,} 条步行净空射线检查，并用 {v['traffic_lane_barrier_rays']:,} 条车道射线检查护栏是否挡路。立交实际桥底净空（包含原道路素材的路面形状）：{clearances}。11 个原建筑贴图字节与原文件一致；{v['placeholder_lots_verified']} 个占位地块的实际屋顶高度已对照规划核验。

18 个区块均重新导入，三角面完整分配，世界坐标最大误差 {dv['maximum_world_position_error_m']:.6f} m；原建筑各一栋、没有丢失，贴图与完整 GLB 一致。道路、地形按完整三角面分配；每个占位地块及其基座按整体分配，避免跨区块切开房屋。

本次交付静态模型、原始素材、生成脚本、区域边界、验证数据和实际渲染图。游戏碰撞、导航、动态加载逻辑和目标设备帧率没有在本次模型导出中配置或测试。

[完整 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal) · [18 区块包](https://chatgpt.com/library?file_id=libfile_e132029f47648191af05ada2095a7858&account_id=personal)
'''

(a.out/'compact_reconstruction_report.md').write_text(report);(compact/'compact_reconstruction_report.md').write_text(report)
readme='''# 三岛城市重构 · 5.8 km²

当前版本为 v8 重构。旧版 4 km 画布与稀疏街面方案已由新岸线、新路网和新地块替代，城市根节点保持米制单位和单位缩放。详见 `design/city/compact/compact_reconstruction_report.md`。

'''+report.split('\n',1)[1]+'''

## 文件及坐标

完整 `huizhou_road_network.glb` 自带贴图；工程包 `design/city/huizhou_road_network.blend` 可继续编辑。原道路素材在 `design/city/road_modular.glb`，11 个原建筑在 `design/city/buildings/`。生成后的规划为 `design/city/city_plan.json.gz`，原 v7 规划保留为 `city_plan_before_compact.json.gz`；旧阶段说明在 `README_history_v7.md`。未标为 compact/v8 的旧审计、改造和 LOD 文件属于历史阶段，不是本次成品数据。

Blender：X 向东、Y 向北、Z 向上；GLB：X 向东、Y 向上、-Z 向北。1 单位 = 1 m。18 区块采用相同世界坐标，导入后根节点位置和旋转归零、缩放为 1，不要逐块居中。16 个陆地区块加 `17_shared_bridges.glb` 和 `18_shared_water.glb` 可以重组完整地图。06 区含两栋 CBD 原建筑，03 区含六栋连续街面及右端转角，02 区含三栋原住宅。

## 重建与验证

使用 Blender 4.5.3 LTS；规划 Python 需 numpy、scipy、Shapely 2.1.2。Blender 的独立 Python 环境需安装匹配版本的 Shapely 和 scipy，并用 `--deps` 指向该依赖目录。原生 .blend 的所有贴图已打包；不必重新生成即可在 Blender 中编辑和导出。

```sh
python3 assets/city/tools/plan_compact_city.py --baseline design/city/city_plan.json --descriptors design/city/compact/source_descriptors.json --out generated/compact-plan
blender -b --factory-startup --python assets/city/tools/extract_road_assets_blender.py -- --roads design/city/road_modular.glb --out generated/road_templates.json
python3 assets/city/tools/prepare_compact_city_meshes.py --plan generated/compact-plan/city_plan.json --templates generated/road_templates.json --out generated/compact-meshes
blender -b --factory-startup --python assets/city/tools/build_compact_city_blender.py -- --plan generated/compact-plan/city_plan.json --meshes generated/compact-meshes --roads design/city/road_modular.glb --models design/city/buildings --deps /path/to/blender-python-deps --out generated/compact
blender -b --factory-startup --python assets/city/tools/validate_compact_city_blender.py -- --glb generated/compact/huizhou_road_network.glb --blend generated/compact/huizhou_road_network.blend --plan generated/compact/city_plan.json --models design/city/buildings --roads design/city/road_modular.glb --build-report generated/compact/compact_build_report.json --deps /path/to/blender-python-deps --report generated/compact/compact_validation.json
blender -b --factory-startup --python assets/city/tools/export_city_districts_blender.py -- --blend generated/compact/huizhou_road_network.blend --plan generated/compact/city_plan.json --out generated/districts --expectations generated/district-expectations --deps /path/to/blender-python-deps
blender -b --factory-startup --python assets/city/tools/validate_city_districts_blender.py -- --districts generated/districts --expectations generated/district-expectations --master-glb generated/compact/huizhou_road_network.glb --deps /path/to/blender-python-deps --report generated/districts/districts_validation.json
```

源包有展开的 `city_plan.json`；Git 仓库压缩保存时可先解开 `city_plan.json.gz`。`render_compact_city_blender.py` 直接渲染原生场景，`draw_compact_city_plan.py` 绘制规划和区块索引，后者需通过 `--font` 提供中文字体。`package_compact_city.py` 仅接受完整模型和全部区块验证通过的数据。

Road Modular：mortalityrexotable，CC BY 4.0，保留原几何截面、UV 和图集；路口以连续沥青补面连接，人行道采用原 Sidewalk 2 素材并重构转角和连接。连接点只保留一个路面归属，避免重叠表面。来源及条款见 `ROAD_ASSET_LICENSE.md`。建筑素材由用户提供，本次未改变其授权范围。
'''
(a.repo/'assets/city/README.md').write_text(readme)
districtreadme=f'''# 城市 18 区块模型 · v8

净陆地 5.80 km²，含跨水桥面约 5.84 km²。此包与完整城市 GLB 是同一成品的两种导入方式。

16 个陆地区块、17 公共跨水桥梁、18 公共海面和湖水。导入时保持世界坐标：根位置 (0,0,0)，根旋转为零，缩放为一；不需要逐块添加偏移。03 区含原六栋相连店面与右端转角，06 区含原两栋 CBD 楼，02 区含原三栋住宅。

18 个 GLB 合计 {total_mb:.2f} MB，最大单块 {largest:.2f} MB。逐区的尺寸、范围和文件名见 `districts_manifest.json`、`district_index.csv` 与 `city_districts_map.png`。分区按完整三角面分配地面、道路和桥梁，并按完整地块保留房屋与基座；相邻包围盒重叠不代表重复面。

所有 18 区块已重新导入验证：三角面无重复或遗漏，世界坐标最大误差 {dv['maximum_world_position_error_m']:.6f} m，11 原建筑各一次，贴图字节保持。游戏加载逻辑、碰撞、导航和运行帧率未配置或测试。Road Modular：mortalityrexotable，CC BY 4.0；建筑为用户提供的素材。
'''
(a.districts/'README.md').write_text(districtreadme)
with (a.districts/'district_index.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['id','name','file','MB_decimal','triangles','source_building_instances'])
    for d in manifest['districts']:w.writerow([d['id'],d['name'],d['file'],f"{d['file_size_bytes']/1e6:.3f}",d['triangles'],';'.join(d['source_building_instances'])])
districtmeta=data/'districts';districtmeta.mkdir(exist_ok=True)
for item in a.districts.iterdir():
    if item.is_file() and item.suffix!='.glb' and not item.name.startswith(('.','huizhou_city_district_map')):shutil.copy2(item,districtmeta/item.name)
for svg in list(districtmeta.glob('*.svg'))+list(a.previews.glob('*.svg')):
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
srcassets=a.source/'assets/city';shutil.copytree(a.repo/'assets/city',srcassets,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(compact,sourcecity/'compact',dirs_exist_ok=True);shutil.copy2(a.plan,sourcecity/'city_plan.json');shutil.copy2(data/'city_plan.json.gz',sourcecity/'city_plan.json.gz');shutil.copy2(before,sourcecity/before.name);shutil.copy2(a.model/'huizhou_road_network.blend',sourcecity/'huizhou_road_network.blend')
shutil.copytree(districtmeta,sourcecity/'districts',dirs_exist_ok=True);shutil.copytree(a.previews,sourcecity/'previews/compact_reconstruction',dirs_exist_ok=True)
def pack(path,root,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for file in files:z.write(file,file.relative_to(root).as_posix())
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    assert path.stat().st_size<512*1024*1024
pack(a.out/'huizhou_city_districts.zip',a.districts,[q for q in a.districts.rglob('*') if q.is_file() and not any(part.startswith('.') for part in q.relative_to(a.districts).parts) and not q.name.startswith('huizhou_city_district_map')])
sourcefiles=[]
for q in a.source.rglob('*'):
    if not q.is_file():continue
    rel=q.relative_to(a.source).as_posix()
    if q.name=='compact_delivery.json':continue # archive hashes live alongside the archives
    if any(part.startswith('.') and part!='.gdignore' for part in q.relative_to(a.source).parts) or '__pycache__' in rel or q.suffix in ['.pyc','.blend1','.blend2']:continue
    if rel.startswith('design/city/previews/') and not rel.startswith('design/city/previews/compact_reconstruction/'):continue
    sourcefiles.append(q)
pack(a.out/'huizhou_city_blender_source.zip',a.source,sourcefiles)
delivery={'schema':'hero13.city.compact-delivery.v8','status':'validated','stats':stats,'model_glb':{'bytes':v['file_size_bytes'],'sha256':hashlib.sha256((a.model/'huizhou_road_network.glb').read_bytes()).hexdigest()},'archives':{q.name:{'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in [a.out/'huizhou_city_blender_source.zip',a.out/'huizhou_city_districts.zip']},'district_glbs':18,'district_bytes':int(total_mb*1e6)}
(a.out/'compact_delivery.json').write_text(json.dumps(delivery,indent=2));(compact/'compact_delivery.json').write_text(json.dumps(delivery,indent=2));print(json.dumps(delivery,indent=2))
