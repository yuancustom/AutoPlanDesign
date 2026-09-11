# P2 文档与代码交付计划

版本0.3.0｜状态：开发设计任务，不是局部编辑已实现。

## 文档必须落到这些模块

| 任务 | 文档/交互 | 待实现代码 | 验收 |
|---|---|---|---|
| P2-01 | 画笔、橡皮、笔宽、平移缩放、选区预览 | 前端 brush/viewport/mask；后端 mask_codec | 相同笔画在高DPI/缩放/平移下回投原图一致 |
| P2-02 | 修改前/后/过程与恢复规则 | revisions/events/artifact_store/jobs | 先持久请求再推理；幂等、并发冲突、拒绝与回滚 |
| P2-03 | 区域编辑与模型配置 | adapters/local_inpaint；compositor | 模型原图独立留存；有效mask以外final像素不变 |
| P2-04 | appearance/layout权限与几何过期 | geometry_patch/impact/approval | 改墙门核心后不继承旧几何；P3入口阻止STALE |
| P2-05 | 固定案例与多模型实验 | benchmark_adapter/integration_tests | 三轮编辑、一次拒绝/回滚/恢复，完整原始证据 |

前后端目标为frontend/和src/autoplan_region/，不表示目录或函数已完成。详细API/schema/数据表在各任务开发前明确，并随代码更新；不能只有一份大Prompt。

## 用户流程

打开指定PlanRevision→选层→涂抹→写指令→核对有效区/保护区→生成候选→前后滑动或并排比较→接受/拒绝。一次操作绑定原版本和楼层，来源变更返回409而不覆盖。

图像context区域大于有效编辑区时，允许模型看周边但不扩大修改授权。用户把“工位改为机柜”写在提示词里，只能触发候选，不自动批准改外轮廓/跨层核心。对布局变更更新几何，不能更新则STALE；只用最新图片生成新模型前必须重建匹配几何。

## 数据与日志

保存before、brush矢量、原分辨率mask、instruction、公开决策摘要、实际prompt/workflow、backend/weight hash、raw_after、final_after、diff、geometry_patch、验证和用户decision。隐藏思维链不作为产品日志要求。失败和拒绝都入attempt，不只保留好图。

版本不可变；撤销是新版本引用旧内容，不能删掉原历史。接口重试用幂等键；多窗口操作用expected_head。本地文件以内容hash寻址，数据库事务引用；恢复先核对已有provider job，避免重复调用。

## 模型测试与实用性

先做无模型mask/合成回放，再适配本地局部重绘候选，最后比较编辑质量。沿用benchmarks候选登记；未经适配/实机确认的模型保持NOT_RUN，不用参数量预言性能。测试原始区外泄漏与最终合成保护分别记分。

验收至少覆盖零选区、整个画布选区、涂到外壳、跨层核心、中文文字区、来源图片变化、崩溃后恢复、16GB资源不足与取消。UI需要明确“当前修改影响哪些层/哪些下游成果”。

## 交接到 P3

输出最新版PlanRevision而不是孤立PNG。用户确认最终平面后再交接；几何hash不匹配或审批版本落后则停止。P2界面可打开P3已生成的旧成果，但必须标“已过期”。

本轮新增此实施映射文档，未实现P2新业务代码；保留已有独立包/合同骨架，下一步从画笔坐标与事件存储启动。
