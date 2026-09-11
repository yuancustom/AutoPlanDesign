# AutoPlanDesign · 三项目协同开发

**开发总控入口：[CONTROL.md](CONTROL.md)**。本轮是架构重整与治理基线，不是三个模型项目已经全部实现。

| 独立项目 | 职责 | 当前状态 |
|---|---|---|
| [P1 / outline-plan](projects/outline-plan/README.md) | 带尺寸闭合轮廓 → 多楼层初步平面图及几何数据 | 旧 L 形示意基线保留；米制校准、通用布局与模型对比待开发 |
| [P2 / region-edit](projects/region-edit/README.md) | 涂抹区域＋文字 → 局部修改、版本与过程记录 | 项目骨架与输入协议；画布、模型及持久化审计待开发 |
| [P3 / plan-delivery](projects/plan-delivery/README.md) | 已确认平面图 → 共享建筑几何 → DXF / PDF / GLB | 已导入用户既有 Skill 的16个文件；Schema和两个检查脚本写入被平台拦截，完整适配为BLOCKED |

## 架构原则

三个项目独立安装、测试、发布；不互相导入内部代码。当前采用单仓库多项目，后续可分别迁出为独立仓库，不提前创建新仓库。最终在 [agent/](agent/README.md) 通过版本化文件协议调用三个能力，不把代码重新混在一起。

图片是展示与交互入口；几何、尺度、版本和证据是串联依据。只有图片的外部输入必须补校准/识图步骤，不能把旧几何套在修改后的图片上。

## 开发者先读

[总控文档](CONTROL.md) · [任务台账](governance/backlog.json) · [接口合同](contracts/README.md) · [模型实验规范](benchmarks/PROTOCOL.md) · [迁移记录](docs/MIGRATION.md)

```bash
python -m pip install -r requirements-dev.txt
python tools/check_governance.py
python -m pytest tests -q
```

各项目可单独运行：进入项目目录，`python -m pip install -e .`，然后 `python -m <模块名> --capabilities`。当前新包只返回真实能力状态，不会生成假平面图、假修改记录或假三维成果。

模块名分别为 `autoplan_outline`、`autoplan_region`、`autoplan_delivery`。旧 P1 基线的复现见其项目 README。

## 当前真实边界

没有在用户 Mac mini 16GB 上完成真实模型对比；所有候选模型实验初始化为 `NOT_RUN`。CI 仅验证治理配置、接口样例、独立项目骨架、历史基线；P3原检查脚本因导入阻塞未运行。不把 CI 成功、mock、dry-run 当成模型效果或工程合规。

旧根目录实现整体保存在 `projects/outline-plan/baseline/`，对应提交 `9be671d75484f497f474aa5b8df23a0a02d429ad`；Git 历史保留。按用户约定直接维护 `main`，本次不创建分支或 PR。
