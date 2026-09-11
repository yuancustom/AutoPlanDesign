# P1 可操作网页原型 v0.3

运行入口：`index.html`，无运行依赖、CDN和模型服务。不需要把图纸上传给第三方。GitHub文件页只显示源码；保存到本机后用浏览器打开，或在此目录执行：

```bash
python -m http.server 8765 --bind 127.0.0.1
```

然后打开 `http://127.0.0.1:8765/`。该命令是静态预览，不是P1后端API。

能操作：受限SVG导入、折线绘制/拖点、缩放平移、撤销重做、等比尺度、尺寸SVG/PNG导出、总量/分层分配校验、模型意向、SHA-256体验快照、过程示例、体验记录导出。完整交互说明在 `../docs/UX_PROTOTYPE_GUIDE.md`。

不能操作：真实后端API、布局求解、任意SVG格式、逐层独立外壳、本地模型生成、成绩评价、正式审批或P2/P3交接。结果三图是固定合成示意，不会按用户输入重排。原型不是完整前后端产品。

测试：

```bash
node --test tests/core.test.cjs
# 浏览器测试需要另行安装playwright并准备本机Chromium：
python tests/browser_test.py --chromium /path/to/chromium --out /tmp/p1-prototype-test
```

浏览器测试使用set_content加载本地HTML以保持零网络。当前环境的导航被管理策略限制，未改该策略；浏览器持久化、Mac/Safari和正式HTTP部署不在这份通过结果中。权重和字体不随原型分发。
