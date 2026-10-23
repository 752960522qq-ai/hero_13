# 夏晴布料测试页

这是当前网页布料测试页的源码快照，Three.js 使用 r180 CDN 模块。在线测试页：
https://xiaqing-motion-lab.expert-eagle-6942.chatgpt.site

## 本地运行

将当前 Site 中的 assets/xiaqing_native_animated.glb 复制到本目录的 assets/xiaqing_native_animated.glb，再从仓库根目录运行：

    cd web-cloth-test
    python3 -m http.server 8080

浏览器打开 http://localhost:8080。页面依赖外网加载 Three.js。

骨骼模型约 25.1 MB，未重复放进仓库；缺少该文件时，网页不能显示夏晴模型。布料求解器可独立运行数值测试：

    node tests/cloth-physics.test.mjs
