# 城市 v12 完整工程

新增两类后巷素材并沿现有楼排加密，后巷从 62 栋增至 80 栋。本次 8 个写字楼模型在 CBD 各使用一次。全城 682 个建筑单元，净陆地 3.25 km²。

完整归档包含可编辑 Blender 工程、全城 GLB、18 个分区 GLB、30 个原始建筑素材、后巷素材池、5 张实际渲染预览、建筑台账和校验脚本。

- 全城 GLB：224,582,688 字节（约 224.6 MB）。
- 原生 Blender 工程：182,194,622 字节（实际字节数见 manifest.json）。
- 完整归档：369,189,652 字节，分为 45 卷，每卷最多 8 MiB。
- 归档 SHA256：`c0a1b059469d6965b2fea9650d82a3fa484b1d99f8bcef5a185c4824beace815`。

下载本目录全部分卷、`manifest.json`、`reassemble.py` 到同一目录。也可以克隆仓库后运行：

```bash
python3 delivery/city_v12/reassemble.py --extract
```

脚本逐一核对分卷、合并归档并校验全部 85 个解压文件。解压后打开 `huizhou_city_v12/huizhou_road_network.blend`，或导入同目录的全城 GLB。18 个区块使用相同世界坐标，保持根节点变换为单位矩阵。

详细变更见 [design/city/v12](../../design/city/v12/README.md)，预览见 [design/city/previews/v12](../../design/city/previews/v12)。请使用整套 v12 区块。
