> 最新版本为 [v10：3.25 km²、640 座建筑](../city_v10/README.md)，本目录保留历史快照；v10 区块不可与本版混用。

# 老城区四栋新增 · v9 完整交付

这里保存了 v9 城市的 33 个二进制分卷。克隆仓库后运行：

```sh
python3 delivery/city_v9/reassemble.py --extract
```

脚本校验每个分卷的 SHA-256、完整压缩包的 SHA-256 和 ZIP CRC，再生成并解压 `huizhou_city_v9.zip`。输出目录为 `delivery/city_v9/huizhou_city_v9/`。重复运行时使用 `--out` 指定另一个输出位置。

包内包含完整城市 `huizhou_road_network.glb`（173.08 MB）、可编辑 `huizhou_road_network.blend`（贴图已打包）、更新后的 03 区、四个原始建筑素材、三张实际渲染图、规划、脚本和验证数据。

12 与 13 号店面已拼成约 55.4 米连续街面并贴着现有人行道；13 与 14 号公寓位于后巷。新增后巷宽 3.6 米，连接两侧街道，四栋新楼的入口高差均小于 1 厘米。原 11 栋建筑位置不变，619 个道路和人行道网格的几何与 UV 与 v8 一致。

已有 v8 全部 18 区块的用户，用本包 `districts/03_main_south_east_center.glb` 替换旧同名文件，并更新清单即可；其他 17 区沿用 v8。18 区已重新导入检查，世界坐标误差为零。完整 GLB 与区块是两种导入方式，选择其中一种。

保存于 Library 的原完整 GLB、源工程包及旧区块分包仍为 v8；本目录为这次新增建筑后的 v9。最新变更见 [说明](../../design/city/compact/oldtown_four_update.md)。
