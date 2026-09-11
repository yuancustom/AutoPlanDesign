# P3 · 画布优先交互原型 V3

任务：P3-UX-01。同步用户确认的 V3 交互方向：独立项目首页、画布工作台、按需浮窗和生成进度。不是旧 V2/V2+ 的常驻三栏卡片界面。

**[HTML 入口](index.html)** · [测试范围](TEST_REPORT.md) · [来源与文件指纹](PROVENANCE.json) · [本轮核验](publication-test.json)

## 怎么打开

GitHub 文件页展示源码，不直接运行 HTML。本轮没有开启 Pages，也没有部署公开网页。

下载仓库并保留 prototype 目录所有 HTML、JS、CSS，然后用浏览器打开 index.html。需要稳定的同源浏览器存储时，在仓库根目录运行：

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory projects/plan-delivery/prototype
```

然后访问 `http://127.0.0.1:8000/`。这是本机静态页面，不是模型服务；不要绑定公网。

也可生成便于保存的独立 HTML：

```bash
python projects/plan-delivery/prototype/build_standalone.py --out runs/p3-prototype/P3_canvas_v3.html
```

构建只读取本目录文件，无网络依赖。独立 HTML 与目录版使用相同脚本顺序和样式。浏览器拒绝 IndexedDB 时仍可使用临时会话；关闭前通过“更多 → 导出标注工程 JSON”备份。移动文件或更换浏览器后，原存储可能不可见。

## 建议体验

选择“发电厂辅助用房” → 点击琥珀色楼梯框复核 → 按 R 在图上拉框 → 填类型、名称和说明 → 保存 → 点击生成图纸与模型 → 明确确认流程演示 → 收起或展开进度 → 打开二维/三维审阅。

| 用户动作 | 当前交互 |
|---|---|
| 选择项目 | 独立首页，进入后不再占左侧；点击顶栏项目名切换 |
| 切换楼层 | 顶栏下拉，每层标注独立；没有常驻楼层卡片 |
| 复核候选 | 点击原图上的框才出现表单；未经修改直接离开不额外确认 |
| 拉框补充 | 松手后就地出现表单，可拖动框角、拖框改位置；保存才创建版本 |
| 查看版本 | 历史按钮按需展开；撤销、重做、恢复均保留历史 |
| 运行演示 | 先确认当前版本；进度浮窗可展开、收起、取消 |
| 审阅结果 | 按需二维/三维分屏；改标注后旧结果过期 |
| 导入自有图片 | 真正加载本地图，不套用示例识别框或无关示例三维 |

快捷键：V 选择，R 补框，H 平移，F 适应画布，O 隐藏/显示标注；空格拖动、滚轮缩放；Ctrl/⌘ Z 撤销，Ctrl/⌘ Shift Z 重做，Esc 关闭当前临时操作。

## 已实现与未接入

真实可用：PNG/JPG/WebP 导入、源图坐标框选、项目/楼层隔离、标注修正、未保存提醒、撤销重做、恢复版本、JSON 标注工程导出/导入、标注 PNG 导出和浏览器本地保存。

演示部分：识别框来自人工预设；进度由页面定时模拟；三维由预设几何绘制，可旋转但不是原图重建。所有模型与 BIMFACE 状态仍为 NOT_RUN。DXF/PDF/GLB 未生成，所以下载按钮禁用。

外部图片仍可手工标注，但不会凭空获得尺度、层高或工程审批。此原型不接生产 API、长期审计、多人并发或真实重建引擎。

## 来源与打包差异

页面结构、交互和视觉来自本次用户已确认的 P3 V3；为便于维护，将单页拆成 index.html、三个 CSS 和八段有序经典脚本。没有运行时导入 P1/P2 代码。

1F 参考图采用已在本仓库 P2 原型中发布的同尺寸 WebP 预览，并在 P3 目录保存独立副本。它由原 PNG 压缩，768×512 画布不变，但并非逐像素/逐字节相同；不是原始测绘底图。2F/3F 仍为程序绘制的演示楼层。原始未压缩图与独立 HTML 继续保留在此前对话完整包中。详见 PROVENANCE.json。

不会提交浏览器 IndexedDB、后续用户导入的私有图纸、私人导出工程、模型权重、字体和凭据。

## 测试

```bash
python -m pip install playwright==1.57.0 'Pillow>=11,<13'
python -m playwright install chromium
python projects/plan-delivery/prototype/build_standalone.py --out runs/p3-prototype/P3_canvas_v3.html
python projects/plan-delivery/prototype/qa/test_ui.py --html runs/p3-prototype/P3_canvas_v3.html --out runs/p3-prototype/interaction
python projects/plan-delivery/prototype/qa/smoke_test.py --standalone runs/p3-prototype/P3_canvas_v3.html --out runs/p3-prototype/loading
```

使用已有 Chromium 时可设置环境变量 P3_CHROMIUM 为其绝对路径。原交互回归有 62 项断言；附加 smoke 检查目录载入、独立文件载入及同源刷新恢复。CI 通过后可从 Actions 下载独立 HTML、实际截图和测试 JSON；不要把静态报告当成某次 CI 的实时结果。
