# 恢复本次编辑

交付 GLB 可以直接用 reassemble.py 重组。需要重新编辑时，在具有完整仓库的环境运行 tools/restore_base_v16.py，指定仓库根目录和一个空工作目录。该脚本校验并恢复 v15 的 06/07/08、元数据、五个原始素材和本版脚本。

Blender 4.5.3；其 Python 环境需 numpy、Shapely 2.1+、scipy。可通过环境变量 HERO13_CITY_DEPS 指定与 Blender 的 Python 版本匹配的依赖目录。工作目录的 tools/build_v16.py 重新生成原生场景；依次运行 validate_v16.py、export_verify_v16.py 验证和导出。本次精确布局在 metadata/layout_v16.json。

渲染器可读取工作目录 context/ 下的其他 v15 区块作为预览上下文；这些区块不会写入本次三个交付 GLB。预览海面也是只读上下文，不包含在增量模型内。
