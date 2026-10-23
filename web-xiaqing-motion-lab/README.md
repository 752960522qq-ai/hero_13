# 夏晴网页测试完整归档

此目录包含当前网页测试项目的完整交付包，包含网页运行文件、测试与验证报告、QA 截图、处理脚本、模型和动作源文件（共 8 个 GLB）。归档按 600 KB 二进制块保存，以适配仓库文件接口的单文件限制；检出仓库后运行 `./restore.sh` 即可解包出 `dist/`、`tests/`、`qa/`、`source-models/`、`source-motions/`、`source-plugins/`、`tools/` 和说明文档。

网页项目源提交：`3d37399f434431dab8a5979f126e284a104c5924`

还原脚本会把归档解压到当前目录。请在仓库根目录运行：

```sh
./web-xiaqing-motion-lab/restore.sh
```

8 个 GLB：
- `dist/assets/xiaqing_native_animated.glb`
- `dist/assets/wardrobe/office_feet_rigged.glb`
- `source-models/body.glb`
- `source-models/current_motion_reference.glb`
- `source-models/office_high_heel_original.glb`
- `source-motions/Idle_raw.glb`
- `source-motions/Run_raw.glb`
- `source-motions/Walk_raw.glb`
