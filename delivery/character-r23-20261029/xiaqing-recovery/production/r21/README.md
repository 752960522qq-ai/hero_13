# 夏晴 R21：武器与新动作

从已恢复的 R20 成品继续制作。本目录包含本轮新保存的 Blender 工程，不代表找回了此前遗失的原 R20 工程。

- 四套角色保留网格、原骨骼静止姿态、原蒙皮及旧动作，追加 Jump 和 Fire。新动作映射 53 个主关节（含 30 个手指关节），同步前臂扭转和肘部辅助骨。
- `actions/*_r21.blend` 为包含新动作且贴图打包的本轮可编辑工程；采样数据和保留检查见 JSON、NPZ。
- `weapons/qbz95_normalized.blend` 是新武器；`type56_reload.blend` 含原网格分离的 Magazine 弹匣。
- 浏览器统一在握持插槽缩放 0.92；枪械网格不做非均匀缩放。相应模型显示长度约为 56 式 0.828 m、汉阳造 1.15 m、QBZ95 0.686 m，采用略缩小的展示比例。
- `dist/weapon-viewer.js` 在 Reload 动作的 14% 取下旧弹匣、30% 松手落地、45% 拿出替换弹匣、75% 装入；中途取消、换装或换武器会重置。弹匣移动以左手握持点为基准，落地后保留 12 秒。
- 前端动作按钮新增跳跃与步枪射击，单次播放后返回待机；可暂停及调速。

尺寸对照：
- https://modernfirearms.net/en/assault-rifles/china-assault-rifles/type-56-eng/
- https://odin.t2com.army.mil/WEG/Asset/QBZ-95_Chinese_5.8mm_Bullpup-Style_Assault_Rifle

本轮只准备本地成果，未发布网站。

可复现步骤（从仓库根目录执行）：

```
blender -b --python production/r21/actions/retarget_new.py
blender -b --python production/r21/actions/finalize.py
blender -b --python production/r21/weapons/build_weapons.py
```

动作脚本从本仓库的 `868dc40` 提交提取 R20 基线，避免重复运行叠加动作。网页换弹逻辑另保存在 `dist/weapon-viewer.js` 中。
