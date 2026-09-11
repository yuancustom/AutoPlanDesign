# P3 开发入口｜plan-delivery

先读根AGENTS.md、CONTROL.md、governance/PARALLEL_CONTROL.md、任务/交付/协调台账、contracts/README.md、本项目README、docs/P3_DEVELOPMENT_v1.0.md、IMPORT.json及vendor内原Skill。文档同步和方向认可不等于建筑审批或BIMFACE外发授权。

只改本项目非vendor路径，禁止改P1/P2、共享合同和根CI。vendor/IMPORT冻结；被平台拦截的三个文件是明确阻塞，不重试绕过、不改名重写来掩盖缺失、不声称原套件通过。父任务P3-01仍BLOCKED。

可向总控申请独立输入准备子任务：已有详细平面图片导入、原图坐标/尺寸/层高证据、置信度与人工确认、错误界面和受控fixture输入适配；必须登记不依赖缺失文件的验收，不能把准备工作当完整重建。P3-D任务先映射总任务ID。进入编码前须有有效认领。

P3可以独立接收图片，不要求P1/P2已运行。不得忠实性不足时自行排房、移动楼梯或统一楼层轮廓。拒绝直接用STALE旧几何；若按当前图片重新识图，先通过ADR/新请求/来源与尺度审批，不静默重标CURRENT。

三种成果必须从同一BuildingIR和revision导出：DXF/PDF/GLB。HTML viewer是应用能力；可选IFC是经授权的内部派生，不能增加第四种建筑成果。不能用图片贴平板或只拉外壳替代真实洞口和层间连接。BIMFACE账号/格式/GLB路径未联调不能承诺可用，凭据只在服务端。

每轮保存handoffs/<session_id>.md，沿用WORK_SESSION模板；分别报告文档/原型/生产/模型/用户验收、实际命令、未测与阻塞。只通过main串行队列发布，不建分支/PR、不强推。真实模型在授权本机串行，失败不自动转云。
