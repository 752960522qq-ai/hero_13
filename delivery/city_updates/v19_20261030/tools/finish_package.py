from pathlib import Path
import json,shutil,gzip,zipfile,hashlib
R=Path(__file__).resolve().parents[1];repo=R.parent/'hero_13';out=repo/'delivery/city_updates/v19_20261030';out.mkdir(parents=True,exist_ok=True)
assert json.load(open(R/'validation/native_validation.json'))['status']=='PASS';assert json.load(open(R/'validation/districts_validation.json'))['status']=='PASS'
for folder in ['tools','annotations','textures','bank_parts']:
 dest=out/('building_bank' if folder=='bank_parts' else folder);shutil.copytree(R/folder,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(R/'tools/restore_building_bank.py',out/'restore_building_bank.py')
(out/'metadata').mkdir(exist_ok=True)
for src,name in [(R/'asset_catalog.json','asset_catalog.json'),(R/'layout.json','layout.json'),(R/'model/site_levels.json','site_levels.json'),(R/'model/build_report.json','build_report.json'),(R/'audit/texture_enhancement.json','texture_enhancement.json')]:shutil.copy2(src,out/'metadata'/name)
(out/'metadata/city_plan.json.gz').write_bytes(gzip.compress((R/'model/city_plan.json').read_bytes(),compresslevel=9,mtime=0));shutil.copytree(R/'validation',out/'validation',dirs_exist_ok=True);shutil.copytree(R/'previews/final',out/'previews',dirs_exist_ok=True)
for p in (R/'renders').glob('*before.png'):shutil.copy2(p,out/'previews'/p.name)
aliases=json.load(open(R/'audit/sources.json'))
for a in aliases:a['original_upload_name']={'S01':'cyberpunk_city.glb','S02':'asian_buildings_set.glb'}.get(a['id'],a['file'])
(out/'metadata/source_inputs.json').write_text(json.dumps(aliases,ensure_ascii=False,indent=2))
prompt='Use case: precise-object-edit. This is an existing UV texture atlas for 3D buildings, an exact technical edit target. Enhance this exact atlas to a crisp 2048 by 2048 or larger square texture: carefully restore fine brick mortar, plaster grain, weathered metal, clear window frame edges. ABSOLUTELY preserve every UV island boundary, object edge, rectangle location, orientation, size, color, the entire composition pixel-aligned at proportional coordinates. Keep all signage exactly as it is, including inverted text; do not correct text or rotate anything. No new windows, no rearranging, no borders, no added shadows or lighting, no invented new architectural elements. Flat albedo texture output filling the full square. The current image is blurry when mapped to building facades, improve only texture detail and edge clarity while leaving all low frequency appearance and all alignments unchanged.'
(out/'metadata/texture_enhancement_prompt.txt').write_text(prompt+'\n\nTool: built-in image generation. Actual output: 1254 x 1254. The resulting atlas was inspected on mapped buildings.\n')
readme='''# 城市 v19：带来源标注的房屋库与五处街区改造

基于 v18 `6a69d2b7d79dbc7d35570fd13cc96216e7472fad`。仅更新 **04、08、09、14** 四块，其余 14 块按原始哈希沿用。

从九份城市素材中分离 **26 种可用房屋**，采用其中 **24 种**、落位 **41 栋**，替换或重新组织原有 **37 栋占位楼**。全城由 543 栋变为 **547 栋**，仍低于 700 栋；老城沿街 120 栋、后巷 80 栋及原正式建筑保留。另有一组铸铁楼的原基础颜色图为纯黑，明确排除，没有作为可用模型交付。

## 布局

- 新城西侧：收紧连续街面，亚洲沿街楼与砖石商住楼围合共享内院。
- 新城东侧：转角与店铺混合，缩减两栋原体块，留出中央口袋花园。
- 新城商务组团：沿既有弯路布置不同高度的办公楼和板式公寓。
- 西岛：坡顶住宅、巷口店铺与花园巷。
- 东岛：厂房、办公室、服务楼围绕装卸院。

道路骨架、海岸、CBD 与天明大厦预留地保留。入口步道按地基边界和路网交点连续调坡；补齐了改造区的地表窄缝及高差路堑侧面。

## 编号与替换对应

`S02-B01-I01` = 来源 S02 / 房屋类型 B01 / 地图实例 I01。独立 GLB 根和部件有来源编号；城市区块内每个源网格有实例编号、来源文件、原节点、替换对象及布局组团。编号写入文件名、模型节点、属性、CSV 和预览，不烙进贴图。

- `annotations/building_asset_catalog.csv`：全部候选、采用/备用/排除状态。
- `annotations/building_map_instances.csv`：41 栋的逐栋对应关系、区块、坐标、旋转与统一缩放。
- `annotations/ANNOTATIONS_zh.md`：九份素材的取舍及贴图处理说明。
- `previews/building_catalog_1.png`、`building_catalog_2.png`：26 种房屋图录。
- `previews/01...05...annotated.png`：实际场景与实例编号。

`S04-B02/B03/B04/B06` 共用的 1024×1024 贴图做 AI 细节增强，实际输出 1254×1254。几何和 UV 保留；增强属于纹理细节重建，其他纹理保留源像素。

## 取得四个城市区块

```bash
python3 reassemble.py --out /new/path/districts
```

脚本校验每个分卷、压缩流及 GLB 的 SHA256。若已有完整 v18，可增加 `--baseline-dir /path/to/v18/districts`，组合为完整 18 块；原目录保留。导入时移除旧 04/08/09/14，再导入同名新块。区块为世界米制坐标，根位置与旋转为零、缩放为一。

## 取得可复用房屋库

```bash
python3 restore_building_bank.py --out /new/path/building_bank
```

恢复 26 份自包含 GLB 与来源目录。独立素材以底部中心为原点，标准高度见目录；地图中的统一缩放见实例 CSV。所有源建筑由用户提供，来源文件与哈希已记录；道路素材说明沿用原项目。

## 验证范围

原生检查覆盖数量、比例、地面连续性、入口通路、邻楼/道路/预留地相交、来源标注、未修改几何与 UV 指纹。四份 GLB 均重新导入核对全部网格位置、三角形、实例属性和内嵌纹理；分卷重组有独立哈希校验。详见 `validation/`。

交付为静态城市区块和房屋素材，尚未接入游戏运行时碰撞、导航或交通。未部署网站。
'''
(out/'README.md').write_text(readme)
(out/'REPRODUCE.md').write_text('''# 复现

复制本目录为独立工作目录 `work_v19`，保留目录结构。需要 Blender 4.5.3 LTS、Python 与 NumPy/SciPy/Shapely；图录另外使用 Pillow 和 Noto Sans CJK SC。

1. `python3 restore_building_bank.py --out .` 恢复 `extracted/`。
2. 设置 `HERO13_REPO_ROOT` 为完整仓库目录，运行 `python3 tools/restore_v18.py` 恢复并校验 16 个本地基准区块及 v18 规划。17/18 共用区块沿用清单，不参与本轮改造。
3. Blender Python 所需第三方包安装到本目录 `deps/`：numpy、scipy、shapely、pillow。规划可直接采用已交付的 `metadata/layout.json`，复制到根目录 `layout.json`；来源目录复制为根目录 `asset_catalog.json`。
4. 在 Blender 后台顺序执行 `tools/build_v19.py`、`tools/repair_surface_holes_v19.py`、`tools/close_road_cuts_v19.py`、`tools/validate_v19.py`、`tools/export_verify_v19.py`。将 v18 清单的 `resolved_districts_manifest` 写为根目录 `baseline_districts_manifest.json`。
5. 渲染 `tools/render_v19.py`，再用普通 Python 执行 `tools/draw_deliverables.py`。图录需要先渲染 `tools/render_catalog.py`；对应字体可从 Noto CJK 官方仓库取得。

提取与原始检查脚本也已保存，若重新提取需用户提供的九份原 GLB 放在工作目录同级的 `upload/`。生产重建可直接使用校验过的房屋库，无需重新生成 AI 纹理。原独立 GLB 已内嵌全部纹理。
''')
shutil.copy2(R/'current_sources_v19.json',repo/'design/city/districts/current_sources_v19.json');shutil.copy2(R/'districts/districts_manifest.json',repo/'design/city/districts/districts_manifest.json');shutil.copy2(R/'validation/districts_validation.json',repo/'design/city/districts/districts_validation.json');vdir=repo/'design/city/v19';vdir.mkdir(exist_ok=True)
for src,name in [(out/'README.md','README.md'),(R/'asset_catalog.json','asset_catalog.json'),(R/'layout.json','layout.json'),(R/'model/build_report.json','build_report.json')]:shutil.copy2(src,vdir/name)
rd=repo/'design/city/districts/README.md';old=rd.read_text();intro='> 最新增量为 **v19**：26 种可用房屋库，24 种落位 41 栋，五处街区改造；全城547栋。仅更新04/08/09/14，其余14块沿用。来源编号、替换对象和坐标见 `delivery/city_updates/v19_20261030/annotations/`；当前来源见 `current_sources_v19.json`。\n\n'
if not old.startswith('> 最新增量为 **v19**'):rd.write_text(intro+old)
dest=R.parent/'deliverables/hero13_city_v19_annotated_update.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
 for pp in sorted(out.rglob('*')):
  if pp.is_file() and 'building_bank' not in pp.relative_to(out).parts:z.write(pp,str(pp.relative_to(out)))
with zipfile.ZipFile(R.parent/'deliverables/hero13_building_bank_v19.zip','a',zipfile.ZIP_DEFLATED) as z:
 if 'metadata/texture_enhancement_prompt.txt' not in z.namelist():z.write(out/'metadata/texture_enhancement_prompt.txt','metadata/texture_enhancement_prompt.txt')
files=[]
for folder in [out,vdir]:
 for pp in sorted(folder.rglob('*')):
  if pp.is_file():files.append(pp)
files.extend([repo/'design/city/districts/current_sources_v19.json',repo/'design/city/districts/districts_manifest.json',repo/'design/city/districts/districts_validation.json',rd]);listing=[]
for pp in files:
 b=pp.read_bytes();listing.append({'local_path':str(pp.resolve()),'repo_path':str(pp.relative_to(repo)),'bytes':len(b),'git_sha':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
(R/'repo_upload_files.json').write_text(json.dumps(listing));print('PACKAGE',dest,dest.stat().st_size,'REPO_FILES',len(listing),flush=True)
