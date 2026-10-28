# 打开与再生成

打开本包 `huizhou_road_network.blend` 或导入全城 GLB 即可查看完整 v12，不依赖旧包。Blender 单位为米；GLB 为 Y 轴向上。

重新生成增量编辑需要 v11 基线：

- 仓库：`752960522qq-ai/hero_13`
- 固定提交：`fa8037848e163a14c0d5c0ab5b3c65e042232e96`
- 目录：`delivery/city_v11`
- 原始归档 SHA256：`4d697acec025448f7290a6c580fcba78d87ab0efe679e2294134038afaca4dc1`
- 合并并解压：`python3 delivery/city_v11/reassemble.py --extract`

使用 Blender 4.5.3 LTS。Blender 内置 Python 为 3.11；向单独的 `blender_deps` 目录安装兼容轮子：

```bash
python3 -m pip install --target blender_deps --python-version 3.11 --only-binary=:all: shapely scipy numpy==2.2.6
```

将本包 `source/new_uploads_manifest.json` 中的 10 个 `source/buildings/<file>` 按 `original_upload_name` 复制到一个 `new_uploads` 目录。原始文件内容不变。再执行：

```bash
blender -b -t 8 --python-exit-code 1 --python tools/build_city_v12.py -- --baseline /path/to/huizhou_city_v11 --uploads /path/to/new_uploads --out /path/to/output/model --sources /path/to/output/source/buildings --deps /path/to/blender_deps
```

先把本包的全部 `source/buildings/*.glb` 复制到输出的 `source/buildings` 目录，保证原有 20 个源文件也在其中。新脚本会复制本次 10 个原始上传文件。

```bash
blender -b -t 8 --python-exit-code 1 --python tools/validate_city_v12.py -- --baseline /path/to/huizhou_city_v11 --model /path/to/output/model --deps /path/to/blender_deps
blender -b -t 8 --python-exit-code 1 --python tools/validate_compact_city_blender.py -- --glb /path/to/output/model/huizhou_road_network.glb --blend /path/to/output/model/huizhou_road_network.blend --plan /path/to/output/model/city_plan.json --models /path/to/output/source/buildings --roads /path/to/source/road_modular.glb --build-report /path/to/output/model/compact_build_report.json --deps /path/to/blender_deps --report /path/to/output/model/compact_validation.json
blender -b -t 8 --python-exit-code 1 --python tools/export_city_districts_blender.py -- --blend /path/to/output/model/huizhou_road_network.blend --plan /path/to/output/model/city_plan.json --out /path/to/output/districts --expectations /path/to/output/expectations --deps /path/to/blender_deps
blender -b -t 8 --python-exit-code 1 --python tools/validate_city_districts_blender.py -- --districts /path/to/output/districts --expectations /path/to/output/expectations --master-glb /path/to/output/model/huizhou_road_network.glb --deps /path/to/blender_deps --report /path/to/output/districts/district_validation.json
blender -b -t 8 --python-exit-code 1 --python tools/render_city_v12.py -- --model /path/to/output/model --out /path/to/output/previews
```

`validate_city_v12.py` 在 0.45 m 间距上加密采样既有后巷，因此原有坡度读数可能比旧版较疏采样略高。它通过原有网格的完整指纹确认旧通路未被改动，并对全部旧、新通路重新核对净空与地形穿插；新增通路单独执行坡度上限检查。
