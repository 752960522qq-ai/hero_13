# 英雄人物测试：制作资料

## 成果
- 双星：复制超人132关节骨架拓扑，按双星的肩、肘、腕、髋、膝、踝和手指比例重设静止骨架；不改变双星原衣服、头部或体形。原模型只做等比米制缩放（总高1.675m）。
- 权重：源表面先按新骨架做空间配准，再按左右手、臂、腿、躯干分别插值4邻域源权重，保留最多4骨影响；头部以头/颈骨过渡绑定。43个网格307015个顶点全部绑定并归一化；所有手指关节均有实际权重。
- 两人均逐个适配 Idle、Walk、Run，含55个主关节（30手指关节）和原扭转辅助骨。动画保留身体上下起伏，去除整体水平位移供站内原地观看。最终GLB在../dist/assets。
- 贴图打包可编辑工程：double_anim/double_stars_animated.blend、superman_anim/superman_animated.blend。
- inputs/保留全部5个原始输入；transfer_report.json、weight_validation.json、ground_final.json及动作报告记录绑定和适配数据。关键帧在两个 *_anim 目录。

## 重现
从本目录执行：
```
blender -b --python superman_anim/clean.py
blender -b --python superman_anim/retarget.py
blender -b --python bind_double.py
blender -b --python double_anim/retarget.py
blender -b --python check_ground.py
```
中间的规范骨架与绑定休止工程会在运行时生成；不需要作为网站运行文件。最终工程、原始素材、脚本和报告均已保存。网页不需要 Blender，使用GLB内的骨架、蒙皮和动作。

模型保留原307015顶点，没有减面。GLB纹理使用JPEG95以使单个模型低于25MiB，不需要额外压缩解码器。
