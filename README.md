# AutoPlanDesign · 三项目协同开发

**开发总控入口：[CONTROL.md](CONTROL.md)**。三个独立项目分别交付文档、代码、测试和使用说明，再组合为完整Agent；不能把文档或交互原型当成生产系统已经实现。

**模型准备：[P1–P3 统一模型需求清单｜Mac mini M4 16GB](docs/MODEL_REQUIREMENTS_M4_16GB.md)**。包含首批与可选模型、权重/量化/运行器、三步骤分工、下载顺序、资源策略及同源对比；实机模型验收仍为 NOT_RUN。

## 三路并行开发入口

**[P1–P3 并行开发控制总览](governance/PARALLEL_CONTROL.md)**：职责/写入边界、任务认领、main串行发布、合同变更、提前联调、五维验收和Mac设备排队。它补充CONTROL，不建立第二套任务台账。

[协调登记（尚无认领）](governance/coordination.json) · [开工与交接模板](governance/templates/WORK_SESSION.md) · [合同变更模板](governance/templates/CONTRACT_CHANGE.md) · [联调报告模板](governance/templates/INTEGRATION_REPORT.md)

各路从项目局部AGENTS.md开始；代码可并行写，发布与同一机器的模型任务串行。登记规则不等于已经部署自动调度器；实际任务仍以backlog和交付状态为准。

## 文档与原型入口（v0.3）

[三项目文档与代码双交付计划](governance/DOC_CODE_DELIVERY.md) · [分维度交付状态](governance/delivery_status.json)

**P1：[可操作原型源码](projects/outline-plan/prototype/index.html) · [运行说明](projects/outline-plan/prototype/README.md) · [交互与体验路线](projects/outline-plan/docs/UX_PROTOTYPE_GUIDE.md)**

**P2：[区域编辑原型](projects/region-edit/prototype/index.html) · [运行说明](projects/region-edit/prototype/README.md) · [详细设计](projects/region-edit/docs/DETAILED_DESIGN_V1.md)**。候选为程序演示，不是已接入模型。

**P3：[画布优先 V3 原型](projects/plan-delivery/prototype/index.html) · [运行与操作说明](projects/plan-delivery/prototype/README.md) · [原型测试范围](projects/plan-delivery/prototype/TEST_REPORT.md)**。独立项目首页、按需补框与版本面板、可折叠进度和二维/三维示意；模型与 BIMFACE 未接入。

**P3：[完整开发设计 v1.0：详细平面图图片重建、BIMFACE 展示与多模型评测](projects/plan-delivery/docs/P3_DEVELOPMENT_v1.0.md)**。用户认可本版方向后，24 章 Markdown 全文已原样同步到 main；[同步与来源核验](projects/plan-delivery/docs/SYNC_v1.0.json)。这是开发依据，不表示业务功能或模型实验已完成。

GitHub文件页显示源码，不会自动运行HTML。将原型保存到本机后用浏览器打开，或按运行说明启动本机静态预览。没有配置Pages或公开原型服务。

P1原型支持受限SVG导入/绘制/拖点、尺寸校准与SVG/PNG导出、分层数量校验、模型意向与快照、示例流程。结果是固定合成示意，不按参数排房，不调用模型，不做正式审批。

| 独立项目 | 职责 | 当前状态 |
|---|---|---|
| [P1 / outline-plan](projects/outline-plan/README.md) | 带尺寸闭合轮廓 → 多楼层初步平面图及几何数据 | 交互原型与设计文档；旧L形基线保留；正式API/通用布局/模型对比待开发 |
| [P2 / region-edit](projects/region-edit/README.md) | 涂抹区域＋文字 → 局部修改、版本与过程记录 | [详细设计](projects/region-edit/docs/DETAILED_DESIGN_V1.md)与可操作原型；生产持久化/局部模型/几何同步待开发 |
| [P3 / plan-delivery](projects/plan-delivery/README.md) | 确认平面 → 三维与二维图纸，网页查看 | V3画布原型与[Viewer计划](projects/plan-delivery/docs/DOC_CODE_PLAN.md)；原Skill缺3文件的导入阻塞保留 |

## 架构原则

三个项目独立安装、测试、发布；不互相导入内部代码。当前采用单仓库多项目，后续可分别迁出为独立仓库，不提前创建新仓库。最终在 [agent/](agent/README.md) 通过版本化文件协议调用三个能力，不把代码重新混在一起。

图片是展示与交互入口；几何、尺度、版本和证据是串联依据。只有图片的外部输入必须补校准/识图步骤，不能把旧几何套在修改后的图片上。

## 开发者先读

[总控文档](CONTROL.md) · [任务台账](governance/backlog.json) · [接口合同](contracts/README.md) · [模型实验规范](benchmarks/PROTOCOL.md) · [迁移记录](docs/MIGRATION.md)

```bash
python -m pip install -r requirements-dev.txt
python tools/check_governance.py
python -m pytest tests -q
node --test projects/outline-plan/prototype/tests/core.test.cjs
```

各项目的Python包仍只提供能力探测骨架。三个浏览器原型是单独代码，不表示已实现正式后端、真实模型和完整工程交付。对应能力状态和阻塞分别记录，不用一个完成标志代替。

## 当前真实边界

没有在用户Mac mini 16GB上完成真实模型对比；模型实验仍为NOT_RUN。CI只验证治理/合同/骨架/历史基线和原型助手；原型浏览器测试范围见其TEST_REPORT。P3原检查脚本因导入阻塞未运行，BIMFACE账号及GLB路径尚未实测。

旧根实现完整保存在 `projects/outline-plan/baseline/`，对应提交 `9be671d75484f497f474aa5b8df23a0a02d429ad`；Git历史保留。按用户约定直接维护main，本次不创建分支或PR。
