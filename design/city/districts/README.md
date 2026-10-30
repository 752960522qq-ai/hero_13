> 最新增量为 **v19**：26 种可用房屋库，24 种落位 41 栋，五处街区改造；全城547栋。仅更新04/08/09/14，其余14块沿用。来源编号、替换对象和坐标见 `delivery/city_updates/v19_20261030/annotations/`；当前来源见 `current_sources_v19.json`。

> 最新增量为 **v18**：十栋正式模型落位，八栋替换老城占位；商场和警察总部进入约 0.150 km² 的东部新城区。老城沿街仍为120栋，全城543栋。仅替换03/08，其余16区块沿用；详见 `delivery/city_updates/v18_20261030/README.md`，来源见 `design/city/districts/current_sources_v18.json`。

> 最新增量为 **v17**：56/57 加入骑楼池，10 型各最多 3 栋；替换 22 栋，老城沿街收紧至 120 栋；12 栋公寓迁入用户圈定内陆地块。仅替换 02/03/04/06/07，其余 13 区块沿用；详见 `delivery/city_updates/v17_20261029/README.md`，来源清单见 `design/city/districts/current_sources_v17.json`。

> 最新增量为 **v16**：12 栋公寓按黄/粉/灰三组布置，剩余高楼改归 CBD；市政区加入办公楼和宿舍并收紧，修复平台黑边。仅替换 06/07/08；详见 `delivery/city_updates/v16_20261029/README.md`，来源清单见 `design/city/districts/current_sources_v16.json`。

> 最新增量为 **v15**：收紧 CBD、内移市政区、修复建筑下陷，误放公寓区的两栋写字楼改归 CBD。只替换实际变动区块；详见 `delivery/city_updates/v15_20261029/README.md`，当前来源清单为 `design/city/districts/current_sources_v15.json`。

# 当前城市区块 · v13 基准 + v14 增量

全城现有 664 座、净陆地 3.25 km²。CBD 29 座已全部采用素材建筑，另保留 172×195 米天明大厦用地，未来 CBD 合计 30 座。

先取得 [v13 完整 18 区块](../../../delivery/city_v13/README.md)，再应用 [v14 六个区块增量](../../../delivery/city_updates/v14_20261029/README.md)：01、05、06、07、08、09。其余 12 个文件保持 v13 的原 SHA256。当前来源见 [current_sources_v14.json](current_sources_v14.json)，当前整套清单与验证见本目录的 districts_manifest.json 和 districts_validation.json。

保持米制、世界坐标和根变换；只移除需要替换的旧区块，再导入新版本。当前 18 个区块组成的模型已经重新导入验证。

本目录保留的旧 GLB、旧地图及旧审计属于历史记录；当前实际模型请从 v13 基准和 v14 增量组合获取。

后续继续按 [区块增量上传约定](../../../delivery/city_updates/README.md)，只上传实际修改区块及必要备注；跨区道路和接缝受影响时同步列明相关区块。
