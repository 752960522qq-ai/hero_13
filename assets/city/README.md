# 三岛城市重构 · 5.8 km²

当前版本为 v8 重构。旧版 4 km 画布与稀疏街面方案已由新岸线、新路网和新地块替代，城市根节点保持米制单位和单位缩放。详见 `design/city/compact/compact_reconstruction_report.md`。


本次重新绘制三岛岸线、街道拓扑和建筑地块，没有整体缩小旧场景。保留 11 个原建筑素材各一栋，原有米制高度和贴图；其他建筑继续使用方块体量。局部道路找平、坡道入口和挡土适配围绕新路网重新生成。

| 项目 | 本次结果 |
| --- | --- |
| 净陆地可玩区边界面积 | 5.80 km² |
| 加入跨水桥面后的平面区域面积 | 5.8357 km² |
| 主岛／西岛净陆地／东岛 | 3.55／1.12／1.13 km² |
| 道路中心线总长 | 67.13 km |
| 道路边／拓扑节点 | 437／249 |
| 道路连通分量 | 1 |
| 新步行街巷 | 119 条，宽 3.6 m |
| 立交及连接匝道 | 2 处／6 条 |
| 最大道路中心线纵坡 | 8.25% |
| 地形标高范围 | 3.00–29.30 m |
| 素材建筑／占位地块 | 11／2995 |
| 全城建筑占地覆盖率／新老城片区覆盖率 | 22.2%／48.1% |
| 完整 GLB | 164.20 MB（十进制） |
| 18 个区块 GLB 合计／最大单块 | 493.06／60.02 MB |

面积按三岛陆地边界扣除湖面计算；海水、湖水不计入。桥面只计算跨水部分，城市立交的上下层不重复增加平面面积。建筑地块属于陆地可玩区边界内，边界面积与游戏导航网格的可行走面积是不同的度量。

老城采用小街坊、沿街连续低层占位和后排院落；CBD 采用裙房与塔楼；外围住宅、大学、市政文化、西岛村镇及东岛工业形成密度和高度层次。六栋原店面总长约 127.02 m，沿现有人行道留约 2.5 cm 收边缝；这段道路局部找平。拐角楼在右端，旋转 90°，原深度方向 1.45 倍适配保留，没有镜像或新增连续雨顶棚。两栋 CBD 素材楼通过顺坡入口广场与人行道连接。

重新导入完整 GLB 后，完成 10,062 处道路表面采样、119 条街巷连续性、入口接缝与 8,118 条步行净空射线检查，并用 66,906 条车道射线检查护栏是否挡路。立交实际桥底净空（包含原道路素材的路面形状）：CENTRAL_DIAMOND：7.55 m、EAST_CITY_FLYOVER：5.91 m。11 个原建筑贴图字节与原文件一致；2995 个占位地块的实际屋顶高度已对照规划核验。

18 个区块均重新导入，三角面完整分配，世界坐标最大误差 0.000000 m；原建筑各一栋、没有丢失，贴图与完整 GLB 一致。道路、地形按完整三角面分配；每个占位地块及其基座按整体分配，避免跨区块切开房屋。

本次交付静态模型、原始素材、生成脚本、区域边界、验证数据和实际渲染图。游戏碰撞、导航、动态加载逻辑和目标设备帧率没有在本次模型导出中配置或测试。

[完整 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)


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


区块已拆为两部分：第1部分包含 01–06、17、18，目前尚未持久保存；[第2部分](https://chatgpt.com/library?file_id=libfile_57ce1917034c8191a950868eba092fba&account_id=personal)包含 07–16。两部分解压到同一目录。完整 GLB 和 Blender 工程包已保存。
