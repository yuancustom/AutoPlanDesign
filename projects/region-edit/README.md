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
