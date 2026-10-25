# 黑色高跟鞋整脚部件

当前只保留 office_feet_rigged.glb 与 office_feet.json。米色高跟鞋模型及其配置已删除。

穿鞋：隐藏人物原脚网格，显示上传的脚＋鞋一体模型；脚踝接缝采用原人物边界位置、法线和骨骼权重，皮肤采用人物原有皮肤材质和贴图。
脱鞋：还原原脚索引和原姿态。原人物 GLB 和 Idle/Walk/Run 动作文件未修改。

四个蒙皮网格（双脚的鞋和皮肤），复用当前人物原生骨架。必须通过 dist/footwear.js 加载配套配置，不能只把资源放到脚骨下而忽略绑定矩阵。

构建：python tools/build_office_feet.py
验证：node --no-warnings --experimental-loader ./tools/three-test-loader.mjs tests/footwear.test.mjs
