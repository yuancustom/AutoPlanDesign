# P3 文档、代码与网页查看交付计划

版本0.3.0｜2026-09-11｜状态：开发设计；原Skill导入阻塞未改变。

## 1. 边界

输入可以是外部已详细设计的多层平面图片，也可以是P2的已确认PlanRevision。独立处理图片时需要尺度、层高、楼层对齐和未知参数台账，不能强依赖P1已经存在。读取共享几何时核对图片/几何版本一致，STALE不进入导出。

遵守vendor原Skill：同一BuildingIR生成DXF（毫米）、PDF、GLB（米/Y-up），图纸说明写入PDF；网页查看是应用功能，不增加第四份HTML建筑交付。不修改原版Skill；适配代码在src/autoplan_delivery/。

## 2. 文档与代码一一对应

| 任务 | 必须写明 | 待开发模块/证据 |
|---|---|---|
| P3-01 输入适配 | 参数来源、缺失问题、审批版本、导入阻塞 | intake_adapter/parameter_ledger/validations；正反fixture |
| P3-02 识图/几何 | VLM输出、宿主墙门窗、楼梯/板洞、尺寸与坐标 | model_adapter/building_ir/geometry_builder；原图与构件对照 |
| P3-03 同源导出 | 单位转换一次、模型空间/排版分离 | exporters/dxf、pdf、glb；回读对象ID和关键尺寸 |
| P3-04 网页查看与验收 | 二维/三维同步选择、楼层/构件开关、版本、格式能力 | frontend/viewer_adapters、readback；真实导出文件的展示截图 |

前端至少有：输入与参数、重建问题清单、二维图纸页、三维模型页、模型对比和交付。版本改变使旧展示标过期；不能保留旧三维截图冒充新重建。

## 3. BIMFACE 优先评估，但不要假定格式/API可用

用户已有BIMFACE会员，二维和三维都希望网页展示。实现采用ViewerAdapter，先对该账号做小文件能力验证，再决定启用哪些BIMFACE路径。会员不是AppSecret/API额度/格式支持或离线授权的证明。

截至本次核对，官方支持列表包括DXF；列表没有给出GLB原生转换的明确依据，因此GLB→BIMFACE不能直接写成已支持。[S1] 先验证二维DXF转换、数据获取、viewToken、构件ID映射与版本更新；三维保持GLB本地浏览适配为基础，BIMFACE通过已确认的格式转换/私有部署方式接入。任何中间格式只在工作区，经批准才使用，不改变三格式交付合同。

AppKey/AppSecret在服务端安全配置；前端仅获得受控查看凭证，不向浏览器暴露服务端认证。BIMFACE官方文档将Access Token用于服务端API认证。[S2] 云转换需要明确文件外发许可；不能用“本地模型”掩盖展示数据外发。用户不授权时不上传，使用本地查看路径。

本轮没有调用用户账号、上传图纸、验证会员权限或实现Viewer。不同用户环境需重新核对，不能把官方格式列表当成账号实测。

## 4. 必须通过的真实检查

三个文件可读、几何匹配、网页显示、人工审查分别记录。DXF回读单位与实际坐标，PDF每页看字/线/比例，GLB看真实墙门窗洞口、楼梯连接、节点层级与坐标变换。不得用一张效果图或平面贴图代替三维几何。

VLM模型可对同一组图纸分别输出BuildingIR候选；用同一建模与导出器比较识别差异，不让每个模型各用不同脚本混淆结果。先合成fixture检验代码，再真实本地模型对比。模型生成可执行代码默认不执行，使用结构化对象和固定几何工具。

## 5. 本轮明确阻塞

IMPORT.json仍登记缺少assets/project.schema.json、scripts/validate_project.py、scripts/validate_deliverables.py。此前平台拦截继续保留，本轮不重试或绕过，不把原检查脚本标为已运行。补齐或经过正式批准的适配方案后，才能验收完整Skill集成。

资料（核对2026-09-11）：
[S1] https://doc.bimface.com/docs/getting-started/v1/developers-guide/supported-translations.html
[S2] https://bimface.com/docs/model-service/v1/developers-guide/access-token.html
