# 跨项目合同变更｜<change_id>

status: PROPOSED
模板不是已批准的变更。提案保存在发起项目 docs/adr/；跨项目决定由总控归档 governance/decisions/。

## 问题与范围
- parent_task_id / proposer / base_main_sha：
- 现行合同版本 / blob或SHA-256：
- 必须解决的具体冲突及例子：
- 受影响的生产方、消费方、历史数据、UI和导出：
- 不改什么：

## 变更设计
- 当前JSON与合法/非法样例：
- 拟议JSON与schema版本：
- 必填、可空、单位、坐标、hash、revision、审批和错误码：
- 向后兼容策略；旧版本拒绝还是显式转换：
- 新/旧数据迁移与回退：
- 生产方与消费方的更新顺序：
- 安全、隐私、文件外发及新增授权：

## 验收与决定
- 正向fixture：
- 缺字段/错版本/未知尺度/STALE/旧批准等负例：
- P1 / P2 / P3测试证据（不涉及则说明）：
- 总控工程决定及事件引用：PENDING
- 用户授权或产品范围决定（需要时）：PENDING
- 生效版本与提交：未生效

只有对应review/授权有证据后才将PROPOSED改为ACCEPTED。未批准的字段不得偷偷写进当前additionalProperties=false合同。不同文档描述冲突不是许可，必须先澄清。
