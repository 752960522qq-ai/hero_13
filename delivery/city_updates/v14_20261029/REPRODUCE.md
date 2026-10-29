# v14 素材落位与复现

| 输入素材 | 用途 | 区块 | 高度 | 正面朝向 |
| --- | --- | ---: | ---: | --- |
| urban skyscraper 3d model 31.glb | CBD 写字楼 | 07 | 80 m | 西 |
| high-rise building 32.glb | 服务式公寓高层 | 06 | 72 m | 北 |
| government building 33.glb | 市政府主楼 | 08 | 26 m | 北 |
| tall office building 34.glb | CBD 写字楼 | 06 | 82 m | 西 |
| high-rise building 35.glb | 服务式公寓高层 | 06 | 78 m | 北 |
| high-rise building 36.glb | 服务式公寓高层 | 07 | 75 m | 南 |
| modern office building 37.glb | CBD 写字楼 | 06 | 36 m | 南 |
| modern building 38.glb | CBD 写字楼 | 06 | 29 m | 南 |
| modern office building 39.glb | CBD 写字楼 | 06 | 26 m | 南 |
| modern office building 40.glb | CBD 写字楼 | 07 | 54 m | 西 |
| glass building 41.glb | CBD 写字楼 | 06 | 24 m | 北 |
| glass building 42.glb | CBD 写字楼 | 06 | 24 m | 东 |
| modern office building 42.glb | CBD 写字楼 | 07 | 54 m | 东 |
| modern office building 43.glb | CBD 写字楼 | 07 | 54 m | 北 |
| modern glass building 44.glb | CBD 写字楼 | 07 | 38 m | 南 |
| glass office building 45.glb | CBD 写字楼 | 07 | 60 m | 东 |
| office building 46.glb | CBD 写字楼 | 06 | 28 m | 北 |
| modern office building 47.glb | CBD 写字楼 | 07 | 28 m | 南 |
| glass office building 48.glb | CBD 写字楼 | 06 | 62 m | 西 |

各输入文件对应一个实例。高层建筑与政府楼仅进行等比缩放、旋转和平移，保持原网格、UV 和贴图。原有 105 个素材实例不移动；1299 个原网格的几何、世界变换和 UV 指纹保持。

## 直接继续编辑

先运行本目录的 `reassemble.py`，得到当前完整 18 个 GLB；这些文件均内嵌贴图，可导入 Blender 继续编辑。当前区块含全部修改结果，不依赖本次临时工作目录。

## 从原始输入重建

自动重建需要 Blender 4.5.3、v13 完整原生工程、此次原始 `1.zip`、`2.zip` 和 31 号 GLB，以及 Blender Python 3.11 的 NumPy 2.2.6、Shapely 2.2 和 SciPy 1.17。压缩包内原文件名应保持，不要互相覆盖“glass building 42”和“modern office building 42”。

`build_city_v14.py` 执行建筑布置、占位楼调整、地形切口和初步入口生成；必须再运行 `finish_city_v14.py` 完成整个前廊投影范围的坡道修整、政府附属楼高度和挡土接缝收口。第一步生成的是施工中间状态，第二步后才是交付状态。

```bash
blender -b -t 8 --python-exit-code 1 --python tools/build_city_v14.py -- --baseline /path/to/v13 --inputs /path/to/19_original_files --out /path/to/model --deps /path/to/blender_python_dependencies
blender -b -t 8 --python-exit-code 1 --python tools/finish_city_v14.py -- --model /path/to/model --baseline /path/to/v13 --deps /path/to/blender_python_dependencies
```

`export_city_incremental_blender.py` 按保留世界坐标的固定分区导出，`--only 1,5,6,7,8,9` 限定本次上传范围；`--baseline-districts` 指向 v13 区块目录。未修改区块保留原文件及 SHA256。`validate_city_v14.py` 检查新增片区与路径，`validate_compact_city_blender.py` 检查道路、立交和建筑，`validate_city_districts_blender.py` 重新导入全部 18 区块检查分配、坐标和贴图。

`render_city_v14.py` 使用 Cycles 24 采样生成实景预览，完整相机参数见 `previews/render_cameras.json`；`plot_city_v14.py` 依据实际坐标绘制二维图，需要系统 Matplotlib 和任意支持中文的字体。此次使用的 Noto Sans SC 来自 Google Fonts 的官方字体仓库。

本次依照增量上传约定没有重复上传整城 GLB、整城 Blender 工程或 12 个未修改区块。规划数据、建筑清单、区块来源与验证记录随本次六个区块一起保存。
