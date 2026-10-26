# 三岛城市道路网络

依据城市概念图和用户提供的 Road Modular 素材，在 Blender 4.5.3 LTS 中完成。地图 4000 × 4000 米，包含北部主城、西部湖泊郊区、东南工业岛及四条跨岛道路。建筑及其他物件继续使用可替换方块。

## 当前模型

[下载 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [下载 Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)

当前版本约 85.49 公里道路，283 个路口，486 栋方块建筑。道路高度 3.0–81.1 米；最大中心线坡度 8.3%。GLB 为 Y 轴向上、北向 -Z；Blender 为 Z 轴向上、北向 +Y，1 单位 = 1 米。GLB 内嵌原素材贴图及地形顶点色。

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

道路素材署名及修改说明见 [ROAD_ASSET_LICENSE.md](ROAD_ASSET_LICENSE.md)。
