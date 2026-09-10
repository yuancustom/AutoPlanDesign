# 发布验证：02 L 形三层试点

日期：2026-09-10。当前发布包含代码、Skill、配置、来源数据、测试和本机执行入口；按用户要求直接维护 main。

## 本轮实际执行

在当前 Linux x86_64 / Python 3.13.5 工具环境，对与待发布 Git blob 一致的源码及规范化输入重新测试：

- `python -m pytest -q --color=no`：47 passed in 4.58s。
- `python scripts/run_pilot.py --mode dry-run --job examples/l_shape_job.json --out <new directory>`：workflow_dry_run_passed。
- 三层各 10 个空间；几何校验 0 错误、0 警告。
- 三层外轮廓对称差面积 0，凹口侵入面积 0；楼梯 A/B、男女卫生间跨层固定。
- 来源栅格与描边多边形 IoU=1.0；该分数不是模型生成图的质量分数。
- 已生成程序 PNG / SVG / 中文 / 离线 HTML 和三个 API 工作流。

工具版本：Pillow 12.3.0，numpy 2.3.5，shapely 2.1.2，requests 2.32.5，pytest 9.0.2。以上不是用户 Mac 的环境锁或性能实测。

详细几何与来源检查分别见 `evidence/publication/geometry_qa.json`、`evidence/publication/source_audit.json`；测试摘要见同目录 tests.txt。远端 CI 成功与否以 Actions 的真实运行结果为准，不提前标记成功。CI 会重新生成三层预览并上传 artifact，不运行生图模型。

## 输入调整说明

为了去掉原截图的文字、色彩渐变和背景噪声，发布版 02.png 使用相同画布的二色蓝色选区；每个被选中的像素与原图相同。它不是原始彩色截图。原图与发布图 SHA-256、阈值规则见 `examples/source_crops/PROVENANCE.json`。规范化没有改变蓝色轮廓几何，l_shape_job.json 同步绑定了新的文件哈希。

## 不能从测试推出的结论

mock 的 FakeSession/纯色 PNG 仅验证接口上传、排队、历史读取与保存，不加载权重。dry-run 不联网，不执行推理。当前没有在用户 Mac 上运行真实模型，也没有完成生成图语义自动验收。

房间布局是针对 L 形编写的明确提案，不是任意轮廓自动优化排房。几何连通不等于实际安全通行，100% 分区不代表墙厚、门扇或设备维护净距已验算。消防、结构、电气、设备荷载及主机组工艺均未审查，不能交付施工。

## 下一步

在用户 Mac 按 `docs/MAC_FIRST_RUN.md` 完成一次真实三层串行生成，保留原图、参数、日志与人工复核，再扩展到第二种形状。
