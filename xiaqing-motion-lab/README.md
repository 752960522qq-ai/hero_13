# 夏晴 R6 · 换装与布料统一测试站

当前入口仅为 `dist/index.html`，包含角色换装与布料测试两个页签。旧鞋履切换、旧衬衫长裤换装和身体拆分系统已移除。

```sh
python3 -m http.server 8000 --directory dist
```

打开 http://localhost:8000 。R6 角色资源为 `dist/assets/vest_xiaqing.glb`，437根骨骼、35个网格、Idle/Walk/Run三套动作。固定站立偏移为 Idle0.017692、Walk0.035238、Run0.046244 米；不会逐帧强制贴地，保留腾空过程。

布料页签复用 `cloth-physics.mjs` 的真实模拟，支持风力、布料拖拽、挂点释放、暂停、复位、地面与人物胶囊碰撞。未实现的衣服选项没有放入界面。

完整制作程序与骨骼/蒙皮/动作独立数据见 [../work/vest-outfit](../work/vest-outfit/README.md)。Blender 参考人体保留在制作工程，不进入运行版GLB。

既有游戏框架保留为 `game.html` 与 `game/`，`index.html?gamePreview=1` 的预览桥接继续支持。原始人物、动作供体与布料来源保留用于溯源；它们不作为旧换装页面恢复入口。

第三方依赖与布料来源许可见 `dist/licenses/` 和 `dist/vendor/`。源文件清单见 `SOURCE_MANIFEST.json`。
