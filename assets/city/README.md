# 三岛城市道路网络

依据城市概念图和用户提供的 Road Modular 素材，在 Blender 4.5.3 LTS 中完成。地图 4000 × 4000 米，包含北部主城、西部湖泊郊区、东南工业岛及四条跨岛道路。CBD 部署两栋用户建筑，老城区部署三栋住宅和六栋相连的沿街建筑；其余建筑及物件继续使用可替换方块。

## 当前模型

[下载 GLB](https://chatgpt.com/library?file_id=libfile_c5007dae2ee081918c343ee1b1e9eabe&account_id=personal) · [下载 Blender 工程包](https://chatgpt.com/library?file_id=libfile_be2e8d31bfd481918c826b823ba4ddae&account_id=personal)

当前版本约 85.66 公里道路，286 个路口，658 栋建筑（11 栋素材建筑、647 栋方块占位）；额外裙楼和港口设施按独立占位物计。道路高度约 3.0–81.1 米；最大中心线坡度 8.26%。完整 GLB 为 210.11 MB（十进制）。GLB 为 Y 轴向上、北向 -Z；Blender 为 Z 轴向上、北向 +Y，1 单位 = 1 米。GLB 内嵌原素材贴图及地形顶点色。

## 当前街面贴合与拐角朝向

六栋连续街面已直接布置在原有 3 m 宽人行道外边缘，不再保留原来的草地退距、独立前置铺装带及四条连接坡道。沿街只设约 2.5 cm 的收边接缝，基座分栋适应街道标高；六栋街面总长约 127.02 m。建筑门槛与本栋沿街人行道的最大标高差约 9.83 cm，城市原有道路、人行道网格和整体坡地保留。旧基座挖空范围已先恢复原地形，再对新基座范围做局部处理。

`urban+building+facade+10.glb` 仍位于面向店面时的最右端，楼体相对其他店面旋转 90°，让原模型的转角立面朝向右侧交叉口。采用旋转，没有镜像建筑或招牌；原素材深度轴乘 1.45 的适配保留。原三栋住宅及两栋 CBD 素材建筑保持位置和比例。

已重新导入检查 11 栋素材建筑和 647 栋占位楼。沿街楼高 11.5–15.2 m，新住宅 14.2 m；占位楼的实际高度与规划最大误差约 0.0000153 m，未发现米、厘米换算或轴向误缩放。街道车行部分为 9 m，两侧人行道各 3 m，总宽 15 m。9 m 对双向两车道的观感偏宽，属于现有道路截面的总车行宽度；没有把它当成两条各 4.5 m 的标准净车道。现实车道宽度资料仅作尺度参照，不作为工程合规结论。

`frontage_alignment.json` 保存本轮移动、朝向和地形处理；`frontage_alignment_validation.json` 保存几何检查，沿街 630 处人行道采样均命中且没有被楼体阻挡；`city_scale_audit.json`、`city_scale_audit.md` 保存尺寸核对。当前预览位于工程包 `design/city/previews/aligned_frontage/`。尺度参照图中的 1.75 m 人形和 4.5 × 1.8 × 1.5 m 汽车只用于该图，不包含在城市或区块 GLB 内。

当前完整 GLB 为 210.11 MB；18 个区块合计 270.15 MB，最大单块 50.92 MB。

### 重建本次街面调整

需要本轮修改前的六栋街面 `.blend`（可从上一个工程版本取得）、`city_plan_before_frontage_alignment.json.gz` 和 `chunk_report_before_frontage_alignment.json`；本轮成品不能重复作为增量输入。工程包附 `frontage_terrain_restore.blend`，仅含两个调整前的原始地形网格，用来恢复旧基座位置。

```sh
gzip -dc design/city/city_plan_before_frontage_alignment.json.gz > /tmp/city-before-frontage.json
gzip -dc design/city/oldtown_expansion_plan.json.gz > /tmp/oldtown-expansion-config.json
blender -b --factory-startup --python assets/city/tools/align_oldtown_frontage_blender.py -- --blend /path/to/before-alignment.blend --restore-terrain design/city/frontage_terrain_restore.blend --plan /tmp/city-before-frontage.json --config /tmp/oldtown-expansion-config.json --chunk-report design/city/chunk_report_before_frontage_alignment.json --deps /path/to/blender-python-packages --out /tmp/aligned-city
blender -b --factory-startup --python assets/city/tools/validate_frontage_alignment_blender.py -- --glb /tmp/aligned-city/huizhou_road_network.glb --plan /tmp/aligned-city/city_plan.json --deps /path/to/blender-python-packages --report /tmp/aligned-city/frontage_alignment_validation.json
blender -b --factory-startup --python assets/city/tools/render_aligned_frontage_blender.py -- --blend /tmp/aligned-city/huizhou_road_network.blend --plan /tmp/aligned-city/city_plan.json --deps /path/to/blender-python-packages --out /tmp/aligned-previews
```

## 前一阶段记录：扩展建筑与开放铺装

本节记录调整前的版本。下述前置步行带和四处街面连接坡道已在当前版本移除，当前布置见上文。

移除上一阶段增加的连续遮雨顶棚、封檐及全部柱列，共 20 个对象；保留素材本身的屋顶和小型门店遮阳篷。原三栋沿街模型与本次三栋街道建筑重新拼为约 127.09 m 的连续街面，位于 M19_Oldtown_South 的 node 242 路口，拐角楼圆角朝向交叉口。新增住宅单独放在原有住宅组团附近。四份新素材均只部署一栋。

| 新素材 | 整体高度 | 适配方式 |
| --- | --- | --- |
| old+urban+building+8.glb | 15.2 m | 等比缩放，拼接连续街面 |
| city+street+building+9.glb | 14.4 m | 等比缩放，拼接连续街面 |
| urban+building+facade+10.glb | 11.8 m | 拐角楼侧向深度乘 1.45，立面宽高比例保留 |
| apartment+building+11.glb | 14.2 m | 等比缩放，独立住宅地块 |

拐角楼连同原地坪的放置深度由约 5.29 m 增至 7.67 m；主体侧面深度约 7.10 m。所有建筑保留原 UV 和贴图，侧向拉伸相应改变该方向的纹理比例。街面共用开放铺装带净宽 2.6 m，转角侧面另接约 2.06 m 宽步道；三处正面入口及一处侧面入口连到原人行道，最大坡度分别约 2.27%、7.57%、3.91%、1.64%。新住宅有 3 m 宽入口步道，最大坡度约 2.08%。五处入口与既有人行道接缝约 6–8 mm，铺装使用 Road Modular 原人行道图集。

本次另移除 `OLDTOWN_Arcade_Blockout_012`、`OLDTOWN_Housing_Blockout_029` 两栋占位。新街面基座范围内局部地形最多下修约 2.9 cm，城市整体坡地保留；道路及人行道几何指纹与本次修改前一致。原两栋 CBD 楼及原两栋住宅未移动。编辑分组为 `20_OLDTOWN_EXPANDED_REAL_BUILDINGS`、`21_OLDTOWN_OPEN_STREET_ADAPTATION`。

`oldtown_expansion.json` 记录实例、位置、侧向比例、基座、步道、移除对象和局部地形调整。`oldtown_expansion_validation_before_frontage_alignment.json` 已通过完整 GLB 重导入、11 栋源建筑、1050 处地坪采样、70 条步行净空射线、转角步道及五个入口检查；`redevelopment_validation.json` 继续检查原始贴图、修复路口、港区入口和内部网格分块。新预览在工程包 `design/city/previews/oldtown_expansion/`。

## 18 个独立区块模型

整个城市拆成 16 个陆地区块、1 个公共桥梁及引道、1 个公共海面与湖水，共 18 个自带贴图的 GLB。全部区块 GLB 合计 270.15 MB，最大单块约 50.92 MB。区块包另附分区图、中文索引、世界坐标边界及验证报告；工程源包内只保留分区说明和数据，18 个区块 GLB 单独交付，不重复打入源包。

导入时保持各文件根节点变换为单位变换：位置 `(0,0,0)`、旋转为零、缩放为一。文件已使用同一城市世界坐标，无需按区块另加偏移，也不要分别居中。公共模型 `17_shared_bridges.glb`、`18_shared_water.glb` 可常驻，其余陆地区块可独立加载；同时加载全部 18 个文件可重组完整城市。已有完整城市 GLB 与区块包内容重复，使用时选择其中一套。

建筑及其基座按整体分配，路面、人行道、地形等按完整三角面分配，保留原始顶点位置、UV、颜色和法线。部分完整建筑或边界三角面跨过逻辑分界，实际边界以 `design/city/districts/districts_manifest.json` 为准；相邻区块包围盒重叠并不表示重复面。六栋连续街面均在 03 区，新住宅在 02 区，CBD 两栋素材楼在 07 区。

18 个 GLB 均已独立重新导入：合计 2,275,331 个三角面，与完整场景一致；源面分配无遗漏或重复，逐区顶点世界坐标核对最大误差为 0，11 栋素材建筑均且仅出现一次，嵌入贴图字节与完整模型一致。详细结果见 `districts_validation.json` 和 `partition_audit.json.gz`。这次完成模型分区；游戏动态加载、碰撞、寻路和目标设备帧率尚未配置或测试。

### 重建本次增量及重新分区

新增建筑的增量脚本必须以本次修改前、含三栋骑楼和新增长雨棚的场景为输入；需要该历史阶段的 `.blend`，不能对当前成品重复运行。`city_plan_before_expansion.json.gz` 和 `chunk_report_before_expansion.json` 保存对应输入数据。Blender Python 需 Shapely 2 和 SciPy，通过 `--deps` 指定目录。

```sh
gzip -dc design/city/city_plan_before_expansion.json.gz > /tmp/city-before-expansion.json
blender -b --factory-startup --python assets/city/tools/plan_oldtown_expansion_blender.py -- --blend /path/to/before-expansion.blend --plan /tmp/city-before-expansion.json --scheme design/city/redevelopment_plan.json.gz --models design/city/buildings --deps /path/to/blender-python-packages --out /tmp/oldtown-expansion-plan.json
blender -b --factory-startup --python assets/city/tools/build_oldtown_expansion_blender.py -- --blend /path/to/before-expansion.blend --plan /tmp/city-before-expansion.json --sites /tmp/oldtown-expansion-plan.json --models design/city/buildings --chunk-report design/city/chunk_report_before_expansion.json --deps /path/to/blender-python-packages --out /tmp/expanded-city
blender -b --factory-startup --python assets/city/tools/validate_oldtown_expansion_blender.py -- --glb /tmp/expanded-city/huizhou_road_network.glb --plan /tmp/expanded-city/city_plan.json --scheme design/city/redevelopment_plan.json.gz --deps /path/to/blender-python-packages --report /tmp/expanded-city/oldtown_expansion_validation.json
blender -b --factory-startup --python assets/city/tools/render_oldtown_expansion_blender.py -- --blend /tmp/expanded-city/huizhou_road_network.blend --plan /tmp/expanded-city/city_plan.json --out /tmp/expanded-previews
```

当前成品可以直接重新导出区块。导出器临时烘焙区块对象，不会覆盖主场景；生成的 `expectations` 是验证临时数据，无需交付。

```sh
blender -b --factory-startup --python assets/city/tools/export_city_districts_blender.py -- --blend design/city/huizhou_road_network.blend --plan design/city/city_plan.json --out /tmp/city-districts --expectations /tmp/district-expectations --deps /path/to/blender-python-packages
blender -b --factory-startup --python assets/city/tools/validate_city_districts_blender.py -- --districts /tmp/city-districts --expectations /tmp/district-expectations --master-glb /path/to/huizhou_road_network.glb --deps /path/to/blender-python-packages --report /tmp/city-districts/districts_validation.json
python3 assets/city/tools/draw_district_map.py --plan design/city/city_plan.json --manifest /tmp/city-districts/districts_manifest.json --out /tmp/district-map
```

## 上一阶段记录：三栋连续骑楼街段

本节记录上一阶段。下述新增顶棚与柱列已经在当前版本移除，三栋楼也已并入上文六栋街面；尺寸、数量和报告只描述当时的状态。

三份新输入资产各部署一次，沿 M19 老城区南街拼为约 56.32 m 长的连续街面，位于原有两栋住宅的街道对面。只移除 `OLDTOWN_Housing_Blockout_032` 一栋占位楼。原四栋真实建筑、道路、人行道和地形网格保持不变。

| 资产 | 整体高度 | 部署数量 |
| --- | --- | --- |
| old+building+facade+6.glb | 11.8 m | 1 |
| storefront+building+7.glb | 11.5 m | 1 |
| urban+building+facade+5.glb | 11.8 m | 1 |

三个模型均等比缩放，保留原 UV 和贴图。按主体墙定位相邻接缝，增设共墙连接，并保留各自原有屋顶轮廓。原模型的地坪外挑和少量底部杂面埋入同一基座；增加简单的连续遮雨顶棚、柱列和廊下地面，使三个店面段之间有清晰的步行连接。顶棚与柱列是可替换的建模体块。

廊道净宽 2.6 m、最低顶棚净高约 3.8 m。地基随原地形埋入，场地高差约 0.39 m；三个 2 m 宽入口缓坡使用 Road Modular 原人行道图集，纵坡约 4.72%、2.06%、3.38%，与原人行道接缝约 6–8 mm。廊道沿长度划分纹理单元，避免整段铺装被拉伸。

`connected_arcades_plan.json.gz` 保存素材基准与选址，`connected_arcades.json` 保存实例及共用地坪、顶棚、接缝和入口，`connected_arcades_validation.json` 保存最终 GLB 重导入检查。检查包括 700 个地坪采样、2.6 m 廊道中的水平净空射线及三个入口的穿地、挡路和接缝；这些几何检查不等于已经配置游戏碰撞和寻路。原始新素材保存在工程包 `design/city/buildings/`，新预览在 `design/city/previews/connected_arcades/`。

重建本次增量时，以加入三栋骑楼前的分块城市 `.blend` 和 `city_plan_before_arcades.json.gz` 为输入；不要对当前成品重复运行。Blender Python 需要 Shapely 和 SciPy，可用 `--deps` 指定其目录。

```sh
gzip -dc design/city/city_plan_before_arcades.json.gz > /tmp/city-before-arcades.json
blender -b --factory-startup --python assets/city/tools/plan_connected_arcades_blender.py -- --blend /path/to/previous-city.blend --plan /tmp/city-before-arcades.json --scheme design/city/redevelopment_plan.json.gz --models design/city/buildings --out /tmp/connected-arcades-plan.json
blender -b --factory-startup --python assets/city/tools/build_connected_arcades_blender.py -- --blend /path/to/previous-city.blend --plan /tmp/city-before-arcades.json --sites /tmp/connected-arcades-plan.json --models design/city/buildings --out /tmp/connected-city
blender -b --factory-startup --python assets/city/tools/validate_connected_arcades_blender.py -- --glb /tmp/connected-city/huizhou_road_network.glb --plan /tmp/connected-city/city_plan.json --scheme design/city/redevelopment_plan.json.gz --report /tmp/connected-city/connected_arcades_validation.json
blender -b --factory-startup --python assets/city/tools/render_connected_arcades_blender.py -- --blend /tmp/connected-city/huizhou_road_network.blend --plan /tmp/connected-city/city_plan.json --out /tmp/connected-city/previews
```

## 实景方案改造基础

- 将老城区及 CBD 的四处近邻道路端点接到既有路口，重新整理路面、坡度、斑马线和人行道。原有 Road Modular 道路网格及人行道图集仍保留；四座跨岛桥均保留。
- CBD 新增 48 个可替换裙楼体块，五处圆形草地调整为小型矩形树池；老城区新增 16 栋骑楼占位、34 栋住宅占位，并连接两栋原有住宅附近的院落步道。行政、大学、文化区各增加一个公共建筑占位，西岛湖区增加 8 栋低层占位。
- 东岛港区增加 3 个平整堆场、集装箱及 3 组岸吊占位；每个堆场都通过 6 m 宽服务车道接入原道路，车道两侧有 1.5 m 人行空间，原路侧人行道在车道入口处开口。主岛南岸补地形贴合的滨水步道，桥头补导向牌和路口信号设施占位。
- 将 17 组道路、人行道、地形和铺装按约 250 m 网格分为 1002 个可独立剔除网格，保持原面片和纹理坐标；是否提升性能需要在目标引擎测试。四栋真实建筑保持原模型，工程包 `design/city/lod/` 另附每栋约 60% 和 30% 面数的可选 LOD 候选。LOD 不会在当前 GLB 自动切换，需在引擎内接入并检查外观。
- 本版重新导入 GLB 并检查七栋真实建筑、原始贴图、四个修复路口、港区入口和堆场地基。路网规划为 1 个连通分量，中心线最大坡度约 8.26%。`plan_validation.json`、`redevelopment_validation.json`、`port_access.json`、`chunk_report.json`、`lod/lod_validation.json` 保存本版结果。游戏内车辆转向、碰撞、人物寻路与实际性能尚待测试；简化建筑与港区设施均为可替换占位。

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
