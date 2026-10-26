# Hero 13

夏晴 R6 换装与布料测试已合并到一个网站，主入口为 `xiaqing-motion-lab/dist/index.html`。旧换鞋、旧换装系统及重复网站目录已移除，可从 Git 历史恢复。

在线入口：[夏晴换装与布料统一测试](https://hero13-xiaqing-motion-lab.lovelysky513.chatgpt.site)。发布记录见 `xiaqing-motion-lab/SITE_PUBLICATION.json`。

## 打开统一网站

```sh
python3 -m http.server 8000 --directory xiaqing-motion-lab/dist
```

打开 http://localhost:8000 。页面包含“角色换装”和“布料测试”两个页签，使用最终 R6 背心短裤角色，提供待机、行走、跑步、视角及骨骼显示；布料支持风、拖动、挂点释放、人物碰撞、暂停与复位。

## 本次完整制作资料

[work/vest-outfit](work/vest-outfit/README.md) 保存最终 Blender 工程、GLB、原始背心人体、制作程序、补丁、437 根骨骼、35 个网格完整蒙皮及三套动作关键帧。工程包含原始人体并排参考；网站使用单角色 GLB。

## 游戏框架

既有三主角游戏框架继续位于 http://localhost:8000/game.html 。保留罗甄、徐哲、夏晴的属性、技能、物品、成长规则和存档；罗甄第六级门槛仍为18000 EXP。

规则见 [GAME_RULES.md](docs/GAME_RULES.md)，接口见 [API.md](xiaqing-motion-lab/dist/game/API.md)。Godot 4.4.1 项目的入口、插件及手机配置保留。

## 来源与许可

原始人物/动作供体、布料来源和第三方许可保留在 `xiaqing-motion-lab/source-*`、`dist/licenses/` 和 `dist/vendor/`。旧分片恢复机制已移除，避免覆盖统一站。
