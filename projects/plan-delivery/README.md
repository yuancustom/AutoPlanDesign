# P3 · 详细平面图图片到 DXF / PDF / GLB 与网页审阅

## 画布优先交互原型 V3

**[HTML 原型入口](prototype/index.html)** · **[运行与操作说明](prototype/README.md)** · [同步测试范围](prototype/TEST_REPORT.md)

P3-UX-01：按用户确认的 V3 同步。项目选择是独立首页，进入后以原图画布为主；楼层、版本、对象表单按需出现。支持真实图片导入、拉框补充、缩放、撤销重做、历史恢复和工程 JSON 导入导出。生成前确认、可折叠进度和二维/三维审阅属于明确标注的流程演示，没有接入模型或 BIMFACE，不提供假的 DXF/PDF/GLB 下载。

下载整个 prototype 目录后打开 index.html，或按说明启动本机静态预览；build_standalone.py 可生成独立 HTML。GitHub 源码页不直接运行页面。本轮不启用 Pages、不更改 P1/P2、vendor、共享数据合同或真实模型状态。参考图使用同尺寸压缩预览，详情在 prototype/PROVENANCE.json。

## 完整开发文档

**[P3 开发设计 v1.0：详细平面图图片 → 三维模型、二维图纸与网页审阅](docs/P3_DEVELOPMENT_v1.0.md)**

2026-09-11，用户认可本版方向后，已将此前交付的 24 章 Markdown 全文原样同步到 main，作为下一阶段的初始开发依据。同步的是完整正文，不是摘要或外部下载链接。文档源文件指纹及范围见 [同步记录](docs/SYNC_v1.0.json)。

原文保留编写时的“开发设计待评审”“本轮未修改 GitHub”等历史表述，以保证与已交付版本逐字节一致；这些句子描述的是文档编写轮次，不代表这次尚未同步。用户对开发方向的认可不替代具体建筑参数/几何审批、BIMFACE 上传授权、内部 IFC 策略和评测阈值的单独确认。

此前文档同步只修改文档与入口，没有改动业务代码、vendor、接口合同、模型实验状态，也没有登录 BIMFACE、上传图纸或执行真实模型推理。本轮另增加上方浏览器原型，不改变这些生产能力边界。

### 后续开发的关键方向

- 首要输入是已经详细设计好的各层平面图图片（IMAGE_ONLY），不要求先运行 P1/P2 或先提供 BuildingIR；匹配几何/CAD 是增强输入。
- 忠实识读已有设计，不擅自移动楼梯、重排房间或统一各层轮廓；真实尺度、层高、对齐和冲突按原 Skill 处理。
- DXF、PDF、GLB 从同一 BuildingIR 生成；二维和三维支持网页审阅，BIMFACE 先做账号和真实文件能力验证。
- GLB 外部构件展示与原生 BIM 语义分开验证；可选 IFC 仅是经授权的内部展示派生，不增加第四种建筑交付格式。
- 固定输入、Skill、工具和预算，对比不同本地视觉语言模型。全部失败、修复、资源消耗与人工纠正都纳入记录。

文档第 21 节列出 P3-D01～P3-D22 任务；实现前应与现有治理任务关联。STALE 图片重新识图等合同澄清须通过 ADR、合同版本及上下游回归落实，不能仅因发布文档就认为接口已升级。

## 当前生产实现状态（未因原型同步而改变）

独立模块：autoplan_delivery。已找到用户完整 Skill 包；16 个原文件冻结导入 vendor；assets/project.schema.json、scripts/validate_project.py 和 scripts/validate_deliverables.py 的写入被平台拦截，导入状态 PARTIAL_BLOCKED。来源、19 个预期 hash 及缺项见 IMPORT.json；补齐前不验收完整集成。原包配套脚本是检查器，不是完整建模引擎；新包目前只报告能力边界。原检查脚本与 Schema 未完整导入，vendor 的测试与执行命令暂不可运行；不将独立骨架测试成功当作 Skill 集成成功。

```bash
cd projects/plan-delivery
python -m pip install -e .
python -m autoplan_delivery --capabilities
python -m unittest discover -s tests -v
```

阅读完整开发文档、仓库 CONTROL.md、IMPORT.json 和 `vendor/floorplan-to-dxf-pdf-glb/SKILL.md` 后开展开发。原 Skill 输入台账、参数来源、审批与共享几何规则保持不变；适配代码放 src，不直接修改 vendor。

建筑交付目录只能有 DXF/PDF/GLB；测试日志和 JSON 留内部工作区。不能用效果图或简单拉伸代替门窗开洞、楼梯连接及同源三格式。没有真实尺度不能伪造米制图纸。
