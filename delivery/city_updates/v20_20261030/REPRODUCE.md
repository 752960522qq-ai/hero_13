# 复现 v20

需要 Blender 4.5.3 LTS，Python 3.11 下的 NumPy、SciPy、Shapely 与 Pillow。将本目录复制为 `work_v20`；仓库位于其同级 `hero_13`。

1. 执行 `tools/restore_baseline.py` 恢复 v19 的当前陆地区块和规划。
2. 在仓库的 v19 目录运行 `restore_building_bank.py --out /path/to/work_v20`，恢复未改动的房屋库。
3. 普通 Python 运行 `tools/plan_v20.py`。规划依赖放入 `deps/`，Blender 依赖放入 `deps311/`；无需重新生成纹理。
4. Blender 后台依次执行 `tools/build_v20.py`、`tools/finish_model.py`、`tools/repair_grades.py`、`tools/finish_walks.py`、`tools/cap_footprints.py`。`finish_model.py` 执行一次，从构建后的原始场景开始；所有 Blender 调用增加 `--python-exit-code 1`。
5. 运行 `tools/validate_v20.py`，通过后执行 `tools/export_verify_v20.py`。导出用的 v19 基准清单取 `metadata/baseline_districts_manifest.json` 放入工作目录根。
6. 渲染 `tools/render_v20.py`；加 `-- before` 获得 v19 对比图。普通 Python 执行 `tools/annotate_v20.py` 和 `tools/package_v20.py`。

来源记录见 `metadata/supplemental_sources.json`，参考分析见 `metadata/reference_layout_notes.md`。编号与图片没有写进建筑贴图。
