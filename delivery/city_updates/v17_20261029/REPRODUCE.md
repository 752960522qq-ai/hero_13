# 恢复 v17 编辑场景

交付 GLB 可直接使用 `reassemble.py` 重组。需要继续编辑时，在完整仓库副本中运行：

```bash
python3 delivery/city_updates/v17_20261029/tools/restore_base_v17.py --repo-root /path/to/hero_13 --work /path/to/work_v17 --context
```

这会验证并恢复 v16 的实际组合输入（02/03/04 来自 v15，06/07 来自 v16），复制两份新源模型、布局和脚本。`--context` 额外恢复只读的 01/05/08，供渲染使用。

使用 Blender 4.5.3。其 Python 环境需 numpy、scipy 和 Shapely 2.1+，可用 `HERO13_CITY_DEPS` 指向匹配 Blender Python 3.11 的依赖目录。依次运行：

1. `prepare_scene_v17.py`：从精确基准创建局部原生场景。
2. `build_v17.py`：创建限量骑楼街段、删减外围占位、公寓内迁及场地。
3. `validate_v17.py`：原生几何、数量、位置与接地检查。
4. `export_verify_v17.py`：导出五区块并逐网格重新导入验证。
5. `validate_textures_v17.py`：普通 Python 加 Pillow，对源贴图与 GLB 内嵌贴图做像素检查。
6. `render_v17.py`：生成四个审阅视角。

Blender 脚本通过 `blender --background --python /path/to/work_v17/tools/<script.py>` 启动。布局依据在 `metadata/layout_v17.json`，最终楼位和街段在 `metadata/layout_v17_resolved.json`；骑楼池及实例上限在 `metadata/arcade_asset_pool.json`。
