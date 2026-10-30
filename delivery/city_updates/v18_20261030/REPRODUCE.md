# 恢复 v18 编辑工作

在完整仓库副本中恢复精确输入：

```bash
python3 delivery/city_updates/v18_20261030/tools/restore_base_v18.py --repo-root /path/to/hero_13 --work /path/to/work_v18 --context
```

脚本逐卷校验并恢复当前组合输入：03 来自 v17，08 来自 v16；`--context` 另恢复其余六个主岛区块，只用于预览。基准城市计划来自固定的 v17 交付元数据。十份新 GLB、来源表及本轮处理脚本会复制到工作目录。

使用 Blender 4.5.3，其 Python 环境需 numpy、scipy、Shapely 2.1+；可用 `HERO13_CITY_DEPS` 指向匹配 Blender Python 3.11 的依赖目录。依次运行：

1. `build_v18.py`：导入精确基准，替换八栋老城占位楼，落位商场及警察总部，重做场地并生成新区边界和用地。
2. `validate_v18.py`：原生数量、原有对象指纹、贴地、道路/邻楼相交、区划与预留地检查。
3. `export_verify_v18.py`：仅导出 03/08，并重新导入逐网格验证。
4. `validate_textures_v18.py`：普通 Python 加 Pillow，检查十份源贴图与导出贴图的 RGBA 像素一致。
5. `render_v18.py`：生成五个实景视角，只读其他主岛区块作为上下文。
6. `plot_v18.py`：普通 Python 加 numpy、matplotlib，绘制实际区划。可用 `HERO13_MAP_FONT` 指向 Noto Sans CJK SC 字体以显示中文；未提供字体时使用英文标注。

Blender 脚本使用 `blender --background --python /path/to/work_v18/tools/<script.py>` 运行。预览的海面不写入交付模型。精确楼位、比例、朝向、来源哈希在 `metadata/new_asset_layout.json`，新区用地在 `metadata/new_town_plan.json`。
