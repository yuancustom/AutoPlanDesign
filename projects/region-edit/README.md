# P2 · 涂抹区域与文字指令局部改图

独立模块：autoplan_region。本轮是骨架与协议，尚无可用涂抹UI/模型服务。详细验收见CONTROL第5节。

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

全文含 18 个章节，覆盖开源调研、涂抹与原图坐标、六类蒙版、局部模型工作流、Mac mini 16GB 候选、不可变版本与恢复、API、P1/P3 交接、任务拆分和验收。设计文档已同步，不代表涂抹 UI 或模型编辑已实现；候选模型实验仍为 NOT_RUN。

用户原始图纸及叠加选区说明图保留在私有对话附件中，不随公共仓库提交。仓库版保留对应操作案例和坐标说明。
