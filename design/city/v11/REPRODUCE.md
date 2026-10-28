# 重建或编辑 v11

直接打开本包 `.blend` 即可编辑；查看成品不依赖旧版本。以下步骤仅用于从上一版重新生成。

使用 Blender 4.5.3 LTS，Blender Python 3.11 依赖 NumPy 2.2.6、Shapely 2.2、SciPy 1.17。先从仓库 `delivery/city_v10/` 重组、解压 v10；其完整快照校验值见 `source/baseline_v10_reference.json`。在本包目录执行以下步骤，将 `BASELINE` 替换为 v10 解压目录，`DEPS` 替换为 Blender Python 依赖目录。

```sh
blender -b --python-exit-code 1 --python tools/build_backlanes_v11.py -- --baseline BASELINE --models source/buildings --out generated/model --deps DEPS
blender -b --python-exit-code 1 --python tools/regrade_walkways_v11.py -- --baseline BASELINE --model-dir generated/model --deps DEPS
blender -b --python-exit-code 1 --python tools/finish_walk_seams_v11.py -- --baseline BASELINE --model-dir generated/model --deps DEPS
blender -b --python-exit-code 1 --python tools/close_terrain_cuts_v11.py -- --baseline BASELINE --model-dir generated/model --deps DEPS
blender -b --python-exit-code 1 --python tools/validate_backlanes_v11.py -- --baseline BASELINE --model-dir generated/model --deps DEPS
blender -b --python-exit-code 1 --python tools/export_city_districts_blender.py -- --blend generated/model/huizhou_road_network.blend --plan generated/model/city_plan.json --out generated/districts --expectations generated/district_expectations --deps DEPS
blender -b --python-exit-code 1 --python tools/validate_city_districts_blender.py -- --districts generated/districts --expectations generated/district_expectations --master-glb generated/model/huizhou_road_network.glb --report generated/districts/districts_validation.json --deps DEPS
blender -b --python-exit-code 1 --python tools/render_backlanes_v11.py -- --model-dir generated/model --out generated/previews
```
