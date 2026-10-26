# 三岛城市道路网络

依据城市概念图和用户提供的 Road Modular 素材，在 Blender 4.5.3 LTS 中完成。地图 4000 × 4000 米，包含北部主城、西部湖泊郊区、东南工业岛及四条跨岛道路。CBD 已部署两栋用户提供的建筑，其余建筑及物件继续使用可替换方块。

## 当前模型

[下载 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [下载 Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)

当前版本约 85.49 公里道路，283 个路口，486 栋建筑（2 栋素材建筑、484 栋方块占位）。道路高度 3.0–81.1 米；最大中心线坡度 8.3%。GLB 为 Y 轴向上、北向 -Z；Blender 为 Z 轴向上、北向 +Y，1 单位 = 1 米。GLB 内嵌原素材贴图及地形顶点色。

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
