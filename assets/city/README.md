# 三岛城市道路网络

根据用户提供的城市概念图和 Road Modular 道路素材，在 Blender 4.5.3 LTS 中完成的城市模型。地图范围 4000 × 4000 米，包含北部主城、西部湖泊郊区、东南工业区，以及四条跨岛道路。约 84.17 公里道路、282 个路口和 496 栋可替换的方块建筑。道路高度约 3.6–93.4 米，地形最高点约 111 米。

## 模型与工程

[下载最终 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [下载 Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)

完整 Blender 工程、原始道路、参考图、预览和设计数据已打包为交付文件 `huizhou_city_blender_source.zip`。解压到仓库根目录后，可编辑工程位于 `design/city/huizhou_road_network.blend`，原始道路位于 `design/city/road_modular.glb`。大型模型及工程通过交付文件保存；仓库内保存生成脚本、压缩的路网设计数据与验证报告。

GLB 内嵌道路贴图、材质和地形顶点色。1 单位 = 1 米；GLB 为 Y 轴向上、北向 -Z；Blender 为 Z 轴向上、北向 +Y。建筑保留 `is_placeholder`、`district` 和 `replaceable_id` 元数据。地形在道路范围内开槽，由道路及路基替代地表。`design/city/.gdignore` 隔离原生工程与参考素材，运行中的游戏入口保持原有配置。

## 重新生成

计划脚本需要 Python、numpy、scipy 和 shapely 2.2。解压工程包后，在仓库根目录运行，将 `blender` 替换为本机 Blender 可执行程序：

```sh
python3 assets/city/tools/create_city_plan.py --out /tmp/hero13-city-plan
blender --background --factory-startup --python assets/city/tools/build_city_blender.py -- --plan /tmp/hero13-city-plan --roads design/city/road_modular.glb --out /tmp/hero13-city-output --render
blender --background --factory-startup --python assets/city/tools/validate_city_blender.py -- --plan /tmp/hero13-city-plan/city_plan.json --glb /tmp/hero13-city-output/huizhou_road_network.glb --report /tmp/hero13-city-output/validation.json
```

`design/city/city_plan.json.gz` 解压后可读取道路节点、分段标高、建筑编号、海岸和湖泊数据。最终 GLB 重新导入后的 18,840 次路面采样全部命中，路口端点最大标高误差小于 0.001 米。完整验证结果见 `design/city/validation.json`。后续可为游戏接入车辆碰撞与导航。

道路素材的署名和修改说明见 [ROAD_ASSET_LICENSE.md](ROAD_ASSET_LICENSE.md)。
