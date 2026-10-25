# 衬衫＋牛仔裤模块替换（本地，未部署）

- 使用上传的 `shirt+trouser.glb`，保留原文件于 `source-models/shirt_trouser_original.glb`。
- Blender 4.3.2 实际构建、绑定并导出九个服装区块；编辑文件为 `shirt_trouser_fitted.blend`。
- 套装统一装备；替换躯干、左右大臂、小臂、大腿、小腿。保留原头、手、脚；套装占用区遮挡原身体及生殖器区域，卸下可恢复。
- 领口保留连续衣料表面，不再向离散原颈部顶点吸附；套装专用颈部过渡由 Blender 收整，卸装恢复原网格。肤色仅在领口和腕部皮肤的纹理区域匹配，衬衫和牛仔裤保留原色。
- 裤脚跟随胫骨，避免受到高跟鞋踝骨额外旋转；袖口处去除了原服装人物的手部残片。
- 脚模块同时控制鞋面和替换脚皮肤；左右独立，未加载鞋款也继承已有隐藏状态。
- 阴茎模块包含阴囊/睾丸表面区域，显示名称改为“阴茎与睾丸”。这部分为原始网格的几何分区，不新增内部器官模型。
- 修正了之前头模块误包含肩部三角面的划分。原角色独立的躯干、生殖器附属网格也归入对应模块，穿套装时同步遮挡，避免原附属表面从裤装穿出。

## 重建

从仓库根目录依次执行：

```sh
python tools/build_body_modules.py
python tools/fit_shirt_trouser.py
python tools/tint_shirt_skin.py
blender -b -t 4 --python tools/blender_fit_shirt_trouser.py
python tools/finalize_shirt_binding.py
blender -b -t 4 --python tools/blender_neck_transition.py
```

最后一步用于将 Blender 的骨骼轴约定转换成网页原角色的绑定轴；不能跳过。Blender 编辑文件保留其自身有效的骨架，网页 GLB 使用转换后的骨架。

## 检查范围

`checks.json` 记录浏览器功能检查；PNG 为待机、行走、跑步各一个时间点的实际网页画面。检查包含六款鞋在左脚隐藏时切换、双脚隐藏、脱鞋恢复，以及九个服装区块隐藏和卸装恢复。

这些为抽样姿势与功能检查，不代表所有动画帧和任意自定义动作均没有穿模。未部署、未推送远程仓库。
