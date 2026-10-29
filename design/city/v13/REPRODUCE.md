# 打开与再生成 v13

打开本包的 Blender 工程，或导入全城 GLB 即可查看完整 v13，打开场景不需要旧版本。单位为米，Blender Z 轴向上，GLB Y 轴向上。

重新生成本次编辑需要 v12 基线：仓库 `752960522qq-ai/hero_13`，固定提交 `258386da312061618708c8f6489e3bf403e51d69`，`delivery/city_v12/`。其归档 SHA256 为 `c0a1b059469d6965b2fea9650d82a3fa484b1d99f8bcef5a185c4824beace815`。下载其全部分卷、manifest 和 reassemble 脚本，运行 `python3 delivery/city_v12/reassemble.py --extract`。

使用 Blender 4.5.3 LTS。向独立目录安装 Blender Python 3.11 兼容依赖：

```bash
python3 -m pip install --target blender_deps --python-version 3.11 --only-binary=:all: shapely scipy numpy==2.2.6
```

将本包 `source/new_uploads_manifest.json` 中四个 `source/buildings/<file>` 按 `workspace_upload_name` 复制到一个输入目录。源文件字节不变。执行：

```bash
blender -b -t 8 --python-exit-code 1 --python tools/build_city_v13.py -- --baseline /path/to/huizhou_city_v12 --uploads /path/to/new_uploads --out /path/to/output/model --sources /path/to/output/source/buildings --deps /path/to/blender_deps
blender -b -t 8 --python-exit-code 1 --python tools/validate_city_v13.py -- --baseline /path/to/huizhou_city_v12 --model /path/to/output/model --deps /path/to/blender_deps
blender -b -t 8 --python-exit-code 1 --python tools/validate_compact_city_blender.py -- --glb /path/to/output/model/huizhou_road_network.glb --blend /path/to/output/model/huizhou_road_network.blend --plan /path/to/output/model/city_plan.json --models /path/to/output/source/buildings --roads /path/to/source/road_modular.glb --build-report /path/to/output/model/compact_build_report.json --deps /path/to/blender_deps --report /path/to/output/model/compact_validation.json
blender -b -t 8 --python-exit-code 1 --python tools/export_city_districts_blender.py -- --blend /path/to/output/model/huizhou_road_network.blend --plan /path/to/output/model/city_plan.json --out /path/to/output/districts --expectations /path/to/output/expectations --deps /path/to/blender_deps
blender -b -t 8 --python-exit-code 1 --python tools/validate_city_districts_blender.py -- --districts /path/to/output/districts --expectations /path/to/output/expectations --master-glb /path/to/output/model/huizhou_road_network.glb --deps /path/to/blender_deps --report /path/to/output/districts/district_validation.json
blender -b -t 8 --python-exit-code 1 --python tools/render_city_v13.py -- --model /path/to/output/model --out /path/to/output/previews
```

`plot_cbd_v13.py` 使用 Matplotlib 绘制精确布局图；它读取脚本所在目录上一层的 `model/city_plan.json`。若需从解压快照直接运行，可创建该目录并复制主规划文件。

原有通路在更密的 0.45 m 间距下进行净空与穿插核查，原有几何以完整指纹确认保持原样；新增通路单独执行坡度上限检查。天明预留用地是零建筑计数的场地网格，后续添加天明大厦时按其记录放置并适配实际裙楼尺寸。
