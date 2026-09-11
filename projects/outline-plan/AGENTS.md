# P1 开发入口｜outline-plan

先读根 AGENTS.md、CONTROL.md、governance/PARALLEL_CONTROL.md、任务/交付/协调台账、contracts/README.md，再读本项目README及docs/P1_DEVELOPMENT_SPEC.md、docs/MODELS_PREPARATION.md、preparation/task_plan.json。

只在本项目非冻结路径开发；baseline只读，不能跨import P2/P3。共享合同、总台账和根CI由总控单写。工作前提交开工卡，认领确认后开始；发布排队到main，不新建分支/PR、不强推。

首个建议任务P1-01：真实单位与尺寸证据、闭合外环/孔洞、像素↔世界变换、冲突拒绝、工程轮廓图导出。未知真实尺寸保持未知，不继承旧L形diagram_units或示例H形尺寸。参数数量由结构化数据校验；不拿原型固定三层图冒充生产布局。

验收先做尺度正常/矛盾、自交/孔洞、非等比拉伸与层间边界测试，再P1-02功能和PlanRevision。产物绑定floor/revision/hash和尺寸事实；跨项目输出未通过合同则不交接。

每轮文档+代码+测试同步，保存handoffs/<session_id>.md（用governance/templates/WORK_SESSION.md）。写清实际命令、原始输出、未测范围、下个任务和阻塞。HTML体验、生产API、模型实测、用户验收分别记录。16GB模型串行并申请设备使用；没跑模型就NOT_RUN。
