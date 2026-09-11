# P2 开发入口｜region-edit

先读根AGENTS.md、CONTROL.md、governance/PARALLEL_CONTROL.md、任务/交付/协调台账、contracts/README.md，再读本项目README、docs/DETAILED_DESIGN_V1.md、prototype/README.md。原型点击通过不代表生产存储或模型已经存在。

只在本项目开发，不改P1/P3/共享合同/根CI；总控确认认领和允许路径后开始。每次一个可验收切片，发布排队到main，不新建分支/PR、不强推。

首轮P2-01验证画笔/保护/撤销、原图像素坐标、缩放/平移/DPR、原分辨率E/P/A/C蒙版。P2-02须满足GOV-01依赖后接持久化、幂等、乐观并发和恢复。未知尺度用内部ImageEditSession提案，不用假米制矩阵绕过PlanRevision 0.1.0。

before/raw-after/final-after/request/mask/event必须可追溯。最终A外像素保持不变；raw泄漏单列。候选不覆盖head，接受/恢复追加revision，拒绝与失败不丢弃。布局未同步几何标STALE；无几何IMAGE_ONLY，不直接让P3米制导出。移动核心需跨层审批，中文和准确对象数量走结构化路径。

不得给P1整图img2img加一句提示词就称局部重绘；必须有真正蒙版适配。外部图片和导出工程默认私有，旧示例的公开授权不能扩展到后来新图。

每轮用governance/templates/WORK_SESSION.md保存handoffs/<session_id>.md。记录实际测试、未实现的多标签/恢复/模型范围、下一任务；模型和用户验收不自批。16GB设备需排队，故障不转云。
