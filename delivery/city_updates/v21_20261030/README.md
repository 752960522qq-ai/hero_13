# 城市 v21：其他来源楼型，一款一栋

基于 v20 `61949bcf57384efdf237fc3169f72a3bbf40042b`，只更新 **04、08、09、10**，其他 14 块保留原 SHA256。

本轮从此前未采用的 4 个来源文件提取 **22 款建筑，各放 1 栋**，替换 **3 栋占位楼**，全城 **604 栋**。新城 12 栋，西岛 10 栋。没有复用这批新楼型；后续接入请遵守每款最多一个地图实例。

| 来源 | 模型编号 | 数量 |
|---|---|---:|
| city (1)(1).glb | S05-B01～B06 | 6 |
| city.glb | S07-B01～B06 | 6 |
| city_street.glb / 补传 city_street(1).glb | S08-B01～B04 | 4 |
| london_city.glb | S09-B01～B06 | 6 |

## 模型标注

按用户要求保留未封口模型：单面/正侧立面、缺背面/屋顶和开放楼板均可纳入，问题没有作为筛除条件。建筑保留原有缺口；场地地坪不作为建筑封口。每款的实际情况写入网格属性、`annotations/model_quality_labels.csv` 和标注预览。S08-B03 为开放楼板施工楼；S08-B04 为灰色店铺商住楼。

建筑采用 `Sxx-Bxx-I01`；本轮不存在 I02。来源文件、原始部件、SHA256、地图坐标、缩放、地坪高度、替换地块均在 `annotations/building_instances_v21.csv`。精确源面选择与归一化矩阵见 `metadata/extraction_selections.json.gz`。

## 布局和贴图

新城道路沿线补入不同轮廓的高楼、街面楼与施工楼；西岛采用转角和短段街面，保留已有弧线道路与公共设施。沿用 v20 地图路网，不改 CBD、老城 120 栋沿街楼和 80 栋后巷楼、天明大厦预留地。

S09 六款共享外墙图集经过图像编辑增强，实际由 **1024×1024 提升到 1254×1254**；没有将其标为 2K。原图和增强图在 `textures/`，提示词在 `metadata/texture_enhancement_prompt.txt`，使用内置图像生成编辑。图集区域位置经目视核对，新增细节属于 AI 解释。替换仅涉及图像字节，几何和 UV 访问器字节保持一致，见 `validation/texture_enhancement.json`。其余保留原贴图，S08 的高密度装饰部件做了减面。

## 还原

```bash
python3 reassemble.py --out /new/path/v21_districts
python3 restore_building_bank.py --out /new/path/v21_bank
```

第一条命令还原四个修改后的 GLB；配合 `--baseline-dir /path/to/v20/districts` 可在新目录组合完整 18 块。第二条还原这批 22 款独立 GLB。分卷最大 8 MiB，分卷、压缩流和 GLB 均检查 SHA256。单位为米，世界坐标不变。

## 验证与限制

原生场景检查、每款一次约束、全部来源标注、建筑与道路/邻楼/预留地相交、入口和周边地面连续性、旧建筑/路网保留检查均通过；四区块导出后重导入检查通过。实际分卷还原结果见 `validation/reassembly_validation.json`。

交付为静态城市模型。未封口情况保留并标注，运行时碰撞、导航、交通和目标设备性能未在本次接入或测试。
