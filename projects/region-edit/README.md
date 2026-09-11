# P2 · 涂抹区域与文字指令局部改图

独立模块：autoplan_region。目前业务模块是骨架与协议；可点击浏览器原型已单独提供，尚未接入生产涂抹 UI、模型服务或长期审计存储。详细验收见 CONTROL 第5节。

## 交互原型

[打开原型目录与操作说明](prototype/README.md) · [HTML 入口](prototype/index.html) · [同步验证](prototype/TEST_REPORT.md)

原型包含编辑工作台、候选对比、版本历史、过程记录和操作与实现五个页面。可以涂抹、撤销笔画、接受/拒绝候选、恢复旧版本并导出/导入工程；恢复产生新版本，不删除历史。候选为程序演示，模型状态仍为 NOT_RUN。

下载仓库并保留 prototype 目录全部文件后，浏览器打开 index.html；GitHub 源码页不直接执行 HTML。prototype/build_standalone.py 可合成单文件，专用 Actions 也会打包生成的 HTML。

## 独立项目骨架

```bash
cd projects/region-edit
python -m pip install -e .
python -m autoplan_region --capabilities
python -m unittest discover -s tests -v
```

首轮开发顺序：画布坐标/原分辨率蒙版 → before/请求先持久化 → 不可变版本与幂等 → 局部模型适配 → raw/final对比 → 用户确认与几何同步。可用合成PlanRevision启动，不必等待P1模型选型。

建议前端Canvas画笔交互，后端Python本机API；框架选型需ADR，不把文档建议当成已安装。至少支持缩放/平移/笔宽/擦除/撤销与预览。

必须保存input/before、brush/mask、prompt/参数、工具步骤、raw-after、final-after、差异、几何补丁、审批/拒绝/错误。蒙版上下文不是修改权限。布局变更后STALE阻断P3。用户历史数据不提交公共GitHub。

## 详细设计文档

[《P2 区域重绘详细设计 v1.0（设计评审稿）》](docs/DETAILED_DESIGN_V1.md)

全文含 18 个章节，覆盖开源调研、涂抹与原图坐标、六类蒙版、局部模型工作流、Mac mini 16GB 候选、不可变版本与恢复、API、P1/P3 交接、任务拆分和验收。设计文档已同步，不代表真实模型编辑已实现；候选模型实验仍为 NOT_RUN。

本次用户明确要求同步原型，因此 prototype 内置了该平面图的同尺寸压缩预览；转换记录见 prototype/PROVENANCE.json。详细设计文档所引用的原始图纸和叠加说明图仍保留在私有附件；浏览器后续导入的图纸、编辑历史和个人工程不会自动上传。
