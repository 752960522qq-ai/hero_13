# 复现

复制本目录为独立工作目录 `work_v19`，保留目录结构。需要 Blender 4.5.3 LTS、Python 与 NumPy/SciPy/Shapely；图录另外使用 Pillow 和 Noto Sans CJK SC。

1. `python3 restore_building_bank.py --out .` 恢复 `extracted/`。
2. 设置 `HERO13_REPO_ROOT` 为完整仓库目录，运行 `python3 tools/restore_v18.py` 恢复并校验 16 个本地基准区块及 v18 规划。17/18 共用区块沿用清单，不参与本轮改造。
3. Blender Python 所需第三方包安装到本目录 `deps/`：numpy、scipy、shapely、pillow。规划可直接采用已交付的 `metadata/layout.json`，复制到根目录 `layout.json`；来源目录复制为根目录 `asset_catalog.json`。
4. 在 Blender 后台顺序执行 `tools/build_v19.py`、`tools/repair_surface_holes_v19.py`、`tools/close_road_cuts_v19.py`、`tools/validate_v19.py`、`tools/export_verify_v19.py`。将 v18 清单的 `resolved_districts_manifest` 写为根目录 `baseline_districts_manifest.json`。
5. 渲染 `tools/render_v19.py`，再用普通 Python 执行 `tools/draw_deliverables.py`。图录需要先渲染 `tools/render_catalog.py`；对应字体可从 Noto CJK 官方仓库取得。

提取与原始检查脚本也已保存，若重新提取需用户提供的九份原 GLB 放在工作目录同级的 `upload/`。生产重建可直接使用校验过的房屋库，无需重新生成 AI 纹理。原独立 GLB 已内嵌全部纹理。
