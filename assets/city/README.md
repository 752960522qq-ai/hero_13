# 三岛城市道路网络

依据城市概念图和用户提供的 Road Modular 素材，在 Blender 4.5.3 LTS 中完成。地图 4000 × 4000 米，包含北部主城、西部湖泊郊区、东南工业岛及四条跨岛道路。CBD 和老城区各部署两栋用户提供的建筑，其余建筑及物件继续使用可替换方块。

## 当前模型

[下载 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [下载 Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)

当前版本约 85.66 公里道路，286 个路口，654 栋建筑（4 栋素材建筑、650 栋方块占位）；额外裙楼和港口设施按独立占位物计。道路高度约 3.0–81.1 米；最大中心线坡度 8.26%。GLB 为 Y 轴向上、北向 -Z；Blender 为 Z 轴向上、北向 +Y，1 单位 = 1 米。GLB 内嵌原素材贴图及地形顶点色。

## 实景方案改造（当前版本）

- 将老城区及 CBD 的四处近邻道路端点接到既有路口，重新整理路面、坡度、斑马线和人行道。原有 Road Modular 道路网格及人行道图集仍保留；四座跨岛桥均保留。
- CBD 新增 48 个可替换裙楼体块，五处圆形草地调整为小型矩形树池；老城区新增 16 栋骑楼占位、34 栋住宅占位，并连接两栋原有住宅附近的院落步道。行政、大学、文化区各增加一个公共建筑占位，西岛湖区增加 8 栋低层占位。
- 东岛港区增加 3 个平整堆场、集装箱及 3 组岸吊占位；每个堆场都通过 6 m 宽服务车道接入原道路，车道两侧有 1.5 m 人行空间，原路侧人行道在车道入口处开口。主岛南岸补地形贴合的滨水步道，桥头补导向牌和路口信号设施占位。
- 将 17 组道路、人行道、地形和铺装按约 250 m 网格分为 1002 个可独立剔除网格，保持原面片和纹理坐标；是否提升性能需要在目标引擎测试。四栋真实建筑保持原模型，工程包 `design/city/lod/` 另附每栋约 60% 和 30% 面数的可选 LOD 候选。LOD 不会在当前 GLB 自动切换，需在引擎内接入并检查外观。
- 本版重新导入 GLB 并检查四栋真实建筑、原始贴图、四个修复路口、港区入口和堆场地基。路网规划为 1 个连通分量，中心线最大坡度约 8.26%。`plan_validation.json`、`redevelopment_validation.json`、`port_access.json`、`chunk_report.json`、`lod/lod_validation.json` 保存本版结果。游戏内车辆转向、碰撞、人物寻路与实际性能尚待测试；简化建筑与港区设施均为可替换占位。

### 从上一版重建改造

需要上一版未分块、含四栋素材建筑的 Blender 场景，以及对应 `city_plan_before_redevelopment.json.gz`；当前成品已分块，请不要对其重复执行增量脚本。Blender Python 需能够导入 Shapely 2 和 SciPy，必要时在各 Blender 命令末尾加 `--shapely-path /path/to/blender-python-packages`。

```sh
gzip -dc design/city/city_plan_before_redevelopment.json.gz > /tmp/city-before-redevelopment.json
blender -b --factory-startup --python assets/city/tools/extract_road_assets_blender.py -- --roads design/city/road_modular.glb --out /tmp/road-templates.json
python3 assets/city/tools/redevelopment_plan.py --plan /tmp/city-before-redevelopment.json --out /tmp/redevelopment-plan
blender -b --factory-startup --python assets/city/tools/repair_redevelopment_roads_blender.py -- --blend /path/to/previous-city.blend --plan /tmp/redevelopment-plan/city_plan.json --scheme /tmp/redevelopment-plan/redevelopment_plan.json --templates /tmp/road-templates.json --out /tmp/repaired
blender -b --factory-startup --python assets/city/tools/build_redevelopment_blender.py -- --blend /tmp/repaired/roads_repaired.blend --plan /tmp/redevelopment-plan/city_plan.json --scheme /tmp/redevelopment-plan/redevelopment_plan.json --old-parks design/city/urban_candidates.json.gz --out /tmp/districts
blender -b --factory-startup --python assets/city/tools/connect_port_yards_blender.py -- --blend /tmp/districts/redeveloped.blend --plan /tmp/districts/city_plan.json --districts /tmp/districts/district_redevelopment.json --out /tmp/port
blender -b --factory-startup --python assets/city/tools/chunk_redevelopment_blender.py -- --blend /tmp/port/connected_city.blend --plan /tmp/port/city_plan.json --out /tmp/final-city --cell-size 250
```

下文记录更早的建设阶段；其中的数量和验证报告属于当时的版本，不代表当前模型的完整状态。

## 道路修整

- 补接 24 处原先悬空或接近其他道路的街道端点，合并短小路口碎段，平顺进出口曲线。
- 道路采用原素材的 Road_33_69 / Double road_36_7 截面和 UV，按接近原有纵向尺度拼接；中央分隔带连续，并在路口前渐变收低。
- 两侧人行道统一为 3 米，使用原素材 Sidewalk 2_1_75 的顶面模型、UV 和台阶高度，沿坡道变形；路口转角补面使用同一图集。人行道按车行路面的完整边界裁切，避免封住路口。
- 路面、人行道和地形使用同一套平面边界；修复裁切地形面朝下造成的黑块。跨海桥及海上汇合处使用连续桥板。
- 调整占用道路边界的方块占位物。本次未改动运行中的游戏入口。

## 验证

实际 GLB 重新导入成功。独立检查道路图与车行路面多边形，均为 1 个连通分量。19,080 次道路采样及 28,937 次人行道采样均命中；未发现地形穿出路面或人行道；地形反向三角面为 0。路口端点最大标高误差 0.0000000 米。报告位于 `design/city/validation.json`、`design/city/topology_validation.json`。

这些检查针对模型几何与道路连通；车辆碰撞及导航仍由后续游戏接入处理。

## 重新生成

工程包解压到仓库根目录后，可编辑场景为 `design/city/huizhou_road_network.blend`。原始道路为 `design/city/road_modular.glb`。仓库保存脚本、设计数据和验证报告；大型模型通过上方交付文件保存。

外部 Python 需要 numpy、scipy、shapely 2.2；Blender 使用自带 numpy。在仓库根目录执行：

```sh
blender -b --factory-startup --python assets/city/tools/extract_road_assets_blender.py -- --roads design/city/road_modular.glb --out /tmp/hero13-road-templates.json
OPENBLAS_NUM_THREADS=1 python3 assets/city/tools/optimize_city_plan.py --baseline design/city/city_plan_baseline.json.gz --templates /tmp/hero13-road-templates.json --out /tmp/hero13-city-plan
python3 assets/city/tools/prepare_city_validation.py --plan /tmp/hero13-city-plan --templates /tmp/hero13-road-templates.json
blender -b --factory-startup --python assets/city/tools/build_city_blender.py -- --plan /tmp/hero13-city-plan --roads design/city/road_modular.glb --out /tmp/hero13-city-output
blender -b --factory-startup --python assets/city/tools/validate_city_blender.py -- --plan /tmp/hero13-city-plan/city_plan.json --glb /tmp/hero13-city-output/huizhou_road_network.glb --report /tmp/hero13-city-output/validation.json
```

`city_plan.json.gz` 为当前优化后的路网，`city_plan_baseline.json.gz` 为优化前的输入快照。原布局生成器 `create_city_plan.py` 仍保留，可重新生成基线。

## CBD 两栋建筑

每个输入模型仅部署一栋，替换 CBD 相邻地块的两栋占位楼，保留原模型长宽高比例、UV 与完整 4096 像素贴图。原始贴图的嵌入字节与用户输入完全一致。玻璃楼入口及办公楼入口均朝向西侧街道。

| 输入资产 | 实际高度 | 原模型及地面区域的宽 × 深 | 替换占位楼 |
| --- | --- | --- | --- |
| modern+glass+2.glb | 68 m | 39.84 × 23.20 m | MAIN_CBD_0189 |
| office+building+1.glb | 44 m | 37.87 × 38.33 m | MAIN_CBD_0188 |

地块分别约有 0.34 m、0.61 m 的原始地面高差。两栋楼使用水平基座，底部埋入原地形，原模型自带地面区域嵌入基座 25 mm；3 m 宽步道与现有人行道相接。基座和入口通道避开车行路面及邻楼。原道路、人行道与地形几何保持不变，详细比例、标高、缓坡及接缝验证见 `design/city/cbd_validation.json`。

原始楼模型位于工程包的 `design/city/buildings/modern_glass_2.glb`、`design/city/buildings/office_building_1.glb`。`cbd_placements.json` 固定地块、旋转与高度；`city_plan_before_cbd.json.gz` 保存部署前的路网规划快照。当前 `.blend` 已包含这两栋可独立编辑的建筑，分组为 `07_CBD_REAL_BUILDINGS`、基座及步道为 `08_CBD_SITE_ADAPTATION`。

在前述道路生成步骤得到基础城市后，运行以下命令重建部署结果：

```sh
blender -b --factory-startup --python assets/city/tools/place_cbd_buildings_blender.py -- --base-blend /tmp/hero13-city-output/huizhou_road_network.blend --plan /tmp/hero13-city-plan/city_plan.json --models design/city/buildings --sites design/city/cbd_placements.json --out /tmp/hero13-city-cbd
blender -b --factory-startup --python assets/city/tools/validate_cbd_buildings_blender.py -- --glb /tmp/hero13-city-cbd/huizhou_road_network.glb --placements /tmp/hero13-city-cbd/cbd_placements.json --report /tmp/hero13-city-cbd/cbd_validation.json
blender -b --factory-startup --python assets/city/tools/render_cbd_buildings_blender.py -- --blend /tmp/hero13-city-cbd/huizhou_road_network.blend --placements /tmp/hero13-city-cbd/cbd_placements.json --out /tmp/hero13-city-cbd/previews
```

道路素材署名及修改说明见 [ROAD_ASSET_LICENSE.md](ROAD_ASSET_LICENSE.md)。

## CBD 铺装和老城区住宅

- CBD 在空地补入 107 栋可替换的建筑体；其占地避让现有楼、道路和人行道，并保留五处小型绿地。
- CBD 原地形上增加约 648,214 平方米的混凝土砖铺装，贴合原地形起伏。铺装按现有地形的道路开口裁切；原有道路、人行道及地形网格未修改。
- 两栋住宅分别使用 `apartment+building+2.glb`、`apartment+building+3.glb` 各一栋，均位于老城区 M19 街区，入口朝向街道。住宅高度分别为 23 米和 23.5 米，按原模型等比缩放。
- 每栋住宅设置埋入地形的水平基座，3 米宽入口步道使用原道路素材的人行道图集，并连接现有人行道；步道最大纵坡分别约 1.02% 和 1.16%，端部高差约 6 毫米。
- 最终 GLB 重新导入后，检查了四栋建筑的数量、比例和原始贴图，住宅基座与步道的地形和路面关系，以及新 CBD 建筑与其他建筑、道路走廊的占用关系。详细结果见 `design/city/urban_validation.json`；几何检查不代表游戏内碰撞和导航已经配置。

工程包中的 `design/city/huizhou_road_network.blend` 已包含全部更新。四栋用户模型、人行道图集和混凝土砖纹理均已保存在工程包内。住宅分组为 `09_OLDTOWN_REAL_BUILDINGS`，CBD 铺装为 `10_CBD_HARDSCAPE`，住宅基座和步道为 `11_OLDTOWN_SITE_ADAPTATION`。

`city_plan_before_urban.json.gz` 保存更新前的规划；`urban_candidates.json.gz` 保存此次地块和绿地选择。要从**更新前、已包含两栋 CBD 建筑**的场景重建本次增量，安装 Blender 对应 Python 的 Shapely 后运行：

```sh
gzip -dc design/city/city_plan_before_urban.json.gz > /tmp/hero13-plan-before-urban.json
gzip -dc design/city/urban_candidates.json.gz > /tmp/hero13-urban-candidates.json
blender -b --factory-startup --python assets/city/tools/urban_update_blender.py -- --blend /path/to/cbd-stage/huizhou_road_network.blend --plan /tmp/hero13-plan-before-urban.json --candidates /tmp/hero13-urban-candidates.json --apartment-2 'design/city/buildings/apartment+building+2.glb' --apartment-3 'design/city/buildings/apartment+building+3.glb' --pavers design/city/textures/cbd_concrete_pavers.png --out /tmp/hero13-urban
blender -b --factory-startup --python assets/city/tools/render_urban_update_blender.py -- --blend /tmp/hero13-urban/huizhou_road_network.blend --update /tmp/hero13-urban/urban_update.json --out /tmp/hero13-urban/previews
```

不要对已完成的当前场景重复运行增量脚本；该脚本要求上述更新前的场景。
