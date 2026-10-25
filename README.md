# Hero 13

三主角游戏框架及夏晴角色动作实验室。可运行的游戏系统位于 `xiaqing-motion-lab/dist/`，采用浏览器 JavaScript 模块；仓库根目录同时保留 Godot 手机项目的启动场景。

## 游戏框架

```sh
python3 -m http.server 8000 --directory xiaqing-motion-lab/dist
```

打开 http://localhost:8000/game.html 。原动作、换装与鞋履实验室位于 http://localhost:8000/index.html ，页面提供游戏框架入口。

- 三主角独立档案：罗甄 `CHR_001`、徐哲 `CHR_002`、夏晴 `CHR_003`。
- 八项属性、行为经验、衍生加成、专属技能、战斗结算、制造书、物品栏及浏览器本地存档。
- 夏晴使用仓库现有模型。其他人物与物品通过固定编号和数据待命，资源可后续接入。
- 演练场可触发行为、攻击与剧情事件，检查技能和成长；原型配置提供专属技能等级预览。

规则、编号与待定参数见 [GAME_RULES.md](docs/GAME_RULES.md)；代码接口见 [API.md](xiaqing-motion-lab/dist/game/API.md)。

本地存档属于当前浏览器，不会同步到其他设备。未给出的罗甄第六级经验、成长速度倍率及专属技能升级获取方式保留配置入口。

## Engine

- Godot 4.4.1 stable
- GDScript
- 2D renderer set to Compatibility for broad mobile-device support
- Portrait viewport: 720 × 1280, scaled with `canvas_items`

## Run

Open this repository folder in Godot 4.4.1 and press Play. The GitHub Actions workflow also imports the project and launches its main scene in headless mode on every push to `main`.

## Android export

Install the matching Godot export templates, OpenJDK 17, Android SDK command-line tools, Android platform/build-tools, and the Android export template. In Godot, configure the Java SDK and Android SDK paths, add an Android export preset, then export a debug APK. The official setup steps are in the [Godot Android export guide](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_android.html).

Godot Engine is MIT licensed. 角色资源及第三方依赖说明见 `xiaqing-motion-lab/` 的资源和许可文件。
