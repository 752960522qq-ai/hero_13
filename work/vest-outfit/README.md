# 夏晴背心替换 · 本次完整交付

最新版本为已发布的 R7，修正待机双臂张开与跑步颈部前探，并加入 Aim 瞄准动作。文件、制作程序、四动作数据与部署记录见 [R7交付](refinement-r7/README.md)。此目录收录本次替换成果、生产程序、源参考与数据，排除废弃模型、日志和缓存；本轮制作资料已同步到 GitHub `hero_13/main`。

## 直接使用

- [Blender 工程（内含原始人体并排参考）](refinement-r6/vest_xiaqing_r6.blend)：可继续编辑的完整场景，包含夏晴头部、角色身体、骨架、全部蒙皮组、Idle / Walk / Run、内嵌材质贴图。
- [角色 GLB](refinement-r6/vest_xiaqing_r6.glb)：35 个角色网格、437 根骨骼和三套动作；不含旁边的原始参考人体。
- [原始背心人体 GLB](refinement-r6/reference_original.glb)。
- [前后对照](refinement-r6/comparison.html)、[制作说明](refinement-r6/README.md)。
- 精简后的角色与布料网站位于 `../../xiaqing-motion-lab/dist/`。

## 程序和可编辑数据

`refinement-r6/build_r6.py`、`lower_restore/apply_lower.py` 和 `lower_patch.npz` 保留最终人体源形恢复、腿部骨架匹配、蒙皮分配与高跟鞋动作适配。没有旧 R5 二进制快照时，程序从本目录最终 Blender 工程加载完整数据，并清理旧参考后重建对照场景；补丁使用绝对坐标与绝对关键帧，可重复应用。先备份工程再执行会生成文件的程序。

```sh
cd work/vest-outfit/refinement-r6
blender -b -t 4 --python build_r6.py
blender -b -t 4 --python export_r6.py
blender -b -t 4 --python extract_editable_data.py
```

`editable_data/` 将关键制作数据以独立格式保存：

- `rig_rest.json`：437 根骨骼的层级、休止矩阵、头尾和继承属性。
- `mesh_manifest.json` + `mesh_skin_data.npz`：35 个网格的休止坐标、面、逐角法线、UV、材质索引、原顶点编号及完整稀疏蒙皮权重；没有把 Blender 内超过四个的原始影响裁掉。
- `animation_manifest.json` + `animation_keys.npz`：三段动作全部曲线路径、分量、关键帧、插值与左右控制柄。材质节点与内嵌贴图以 `.blend` 为准，运行版以 GLB 为准。

`production_history/` 保留实际开发使用的初始移植、头颈分割、肩部修复、原鞋恢复、权重转移和动作修改程序，以及需要的编号、坐标和补丁数据。它保留阶段内的原始引用，供追溯算法；早期中间 `.blend` 快照不重复上传。当前继续编辑和重导出使用上面的 R6 工程与程序。

原生夏晴骨骼/动作来源已在仓库 `xiaqing-motion-lab/dist/assets/xiaqing_native_animated.glb`，SHA256 为 `df85a35cbbee722c2b4ad3af72aabc41b224c9d50b739a924837f1467e3b9c45`，与本次使用的源文件一致，不重复存第二份。

`INVENTORY.json` 提供本目录文件的路径、大小和 SHA256（不包含清单自身）。
