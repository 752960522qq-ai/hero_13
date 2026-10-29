# 城市 v13 完整工程

CBD 收紧至 29 座现有建筑：14 座用户素材楼、15 座占位楼。另留 172×195 m、33,540 m² 的天明大厦用地，未来放入天明大厦后 CBD 合计 30 座。全城现有 652 座，净陆地 3.25 km²。

本目录包含完整归档的 52 个分卷，每卷最多 8 MiB。归档 429,420,632 字节，SHA256：`abf8173a0fc7df91c8b4f41f7cfbe41ea791597794fddc5e04e94482c85d4a41`。

全城 GLB 为 247,160,032 字节，原生 Blender 为 205,165,422 字节。包内有 18 个区块、34 个原始建筑素材、建筑清单、天明预留地记录、5 张预览和再生成脚本。

下载本目录全部分卷、`manifest.json`、`reassemble.py` 到同一目录，或克隆仓库后运行：

```bash
python3 delivery/city_v13/reassemble.py --extract
```

脚本核对分卷与归档，安全解压并验证全部 94 个文件。解压后打开 `huizhou_city_v13/huizhou_road_network.blend`，或导入同目录的全城 GLB。区块已使用统一世界坐标，保持根节点单位变换，使用整套 v13。

详细说明：[design/city/v13](../../design/city/v13/README.md)。预览：[design/city/previews/v13](../../design/city/previews/v13)。
