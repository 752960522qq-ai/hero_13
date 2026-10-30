# 复现 v21

使用 Blender 4.5.3 LTS、Python 3.11 的 NumPy/SciPy/Shapely/Pillow。工具根目录命名为 work_v21，与 hero_13 同级。

1. 运行 tools/restore_baseline.py 还原 v20 区块与规划；deps 和 deps311 分别提供系统 Python 和 Blender Python 依赖。
2. 四个原始 GLB 按 metadata/source_inputs.json 的 SHA256 准备。audit_new_sources.py 检查源文件；extract_new_buildings.py 提取。若仅恢复资产库，直接运行 restore_building_bank.py。
3. textures/S09_city_facades_enhanced.png 放入工作目录 textures，原始图放入 audit/source_WorldCityBuildings2.png；从原始文件重新提取时运行 apply_source_enhancement.py，直接还原建筑库时跳过（已包含增强贴图）。增强使用内置图像编辑，保存了原图、增强图、提示词和实际尺寸。
4. 运行 plan_v21.py。22 款每款只能出现一次，这一约束同时在规划、模型属性与验证中检查。
5. Blender 后台运行 build_v21.py、validate_v21.py；每次调用使用 --python-exit-code 1。构建优先读取缓存的 v20 原生场景，没有缓存时导入四个 v20 GLB。
6. 验证通过后运行 export_verify_v21.py。渲染 render_v21.py，附加 -- before 渲染 v20 对比；render_asset_gallery.py 生成素材预览；annotate_v21.py 生成标注图，package_v21.py 打包。

构建不会修补源楼体缺口；仅增加场地地坪、入口和来源标注。每栋楼的选择面和归一化矩阵在 metadata/extraction_selections.json.gz。
