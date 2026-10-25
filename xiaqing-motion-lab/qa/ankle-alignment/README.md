# 裤脚与脚踝对齐修复

原问题：裤管用固定中心拟合，与原生小腿后侧轮廓偏差约 5–20mm，穿衣后保留的皮肤从裤管穿出。衣物切换前后鞋子坐标实际未变。

Blender 4.3.2 按左右小腿各自的截面重新拟合，下面 27cm 完整校正，27–34cm 平滑衰减。GLB 仅替换两块小腿网格的位置/法线数据；其它缓冲区保留。

- `trouser_ankles_corrected.blend`：可编辑衣物模型。
- `blender-refit.json`：局部拟合参数。
- `preservation.json`：原始资源的逐项比对结果。
- `runtime-checks.json`：63 组换鞋、动作、穿脱检查，鞋坐标偏移为零。
- `blender-posed-checks.json`：三个实际网页动作姿态共 228 点，最小内侧余量 1.49mm，无采样点外穿。
- `*_after.png`：浏览器与 Blender 近景，`Idle_before.png` 是修复前对照。

复现：从 dist 启动 8765 HTTP 服务，运行 `python3 tools/verify_trouser_ankle_alignment.py`，再运行 `blender -b --python tools/blender_verify_trouser_ankles.py`。需 Playwright、Chromium 和 Blender。测试会生成被忽略的姿态网格与 Blender 场景。

未进行手机实机或全部动作帧验证。SOURCE_MANIFEST.json 和上传 ZIP 是原始上传快照，未改写。
