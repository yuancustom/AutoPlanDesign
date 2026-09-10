# AutoPlanDesign

建筑外轮廓 → 多楼层功能布局 → 本地模型表现 → 中文标注与拼版。

首个试点：用户指定的 **02 L 形建筑，1F / 2F / 3F**。代码按用户要求直接维护在 `main`，不要求创建功能分支或 Pull Request。

## 当前能力与验证边界

| 环节 | 当前结果 |
|---|---|
| L 形来源绑定、三层功能布局 | 已实现；三层各 10 个空间 |
| 房间、门、核心与轮廓几何检查 | 已通过 |
| 自动测试 | 本次发布前 47 项通过；远端结果见 Actions |
| 三层 PNG / SVG / 中文 / 离线 HTML | 程序生成，首跑可以复现 |
| ComfyUI 接口工作流 | dry-run 已通过；mock 只验证协议 |
| 用户 Mac 上的真实模型推理 | 尚未验证 |
| 任意轮廓自动最优排房 | 未实现；当前为明确的 L 形布局提案 |
| 消防、结构、设备工艺审查 | 未执行；输出不是施工图 |

**程序几何图、dry-run、mock、真实模型原图是不同产物，不能相互冒充。** GitHub Actions 只运行几何与协议测试，不下载或运行生图模型。

## 先跑一栋三层

在 Apple Silicon Mac mini 16GB 上，新建独立环境，不与现有 IOPaint / DocRes 环境混用：

```bash
git clone https://github.com/yuancustom/AutoPlanDesign.git
cd AutoPlanDesign
conda create -n autoplan-tools python=3.12 -y
conda activate autoplan-tools
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_pilot.py --mode geometry --job examples/l_shape_job.json --out runs/l-shape-first
open runs/l-shape-first/preview.html
```

每次使用新的输出目录，不覆盖旧结果。没有 Conda 时可用独立 Python 3.11+ venv。

工作流预演，不加载模型：

```bash
python scripts/run_pilot.py --mode dry-run --job examples/l_shape_job.json --out runs/l-shape-dry-01
```

本机 ComfyUI、SD1.5 checkpoint 和匹配 Canny ControlNet 安装好后，填写 `configs/comfy_sd15.json`：

```bash
python scripts/doctor.py --out runs/mac-check.json
python scripts/run_pilot.py --mode render --ack-concept-only --job examples/l_shape_job.json --out runs/l-shape-model-01
```

真实模式只访问本机服务，三个楼层串行；失败即停止，不转云端。模型输出保存在 `generated/`，合成结果叫 `board_model_unreviewed.png`。必须检查原始模型图片后再做概念验收。

## 楼层分工

1F：辅助机房、机柜区、配电辅助间、运行办公室与值班室。

2F：控制室、通信机柜区、技术办公室、小会议室与资料室。

3F：综合办公室、会议室、资料室、设备保障间与值班室。

三层固定楼梯 A/B、男女卫和公共交通；楼梯数量只是演示配置，不是合规结论。只有一个输入轮廓，因此明确假设三层同轮廓；不发明退台、悬挑、米制比例尺或北向。

## 文件入口

- [Agent 入口](AGENTS.md) 与 [现行 Skill](skills/outline-floorplan-local/SKILL.md)
- [Mac 首跑说明](docs/MAC_FIRST_RUN.md)
- [实施与验证报告](docs/IMPLEMENTATION_REPORT.md)
- [源图处理说明](docs/PROVENANCE.md)
- [L 形三层布局数据](examples/l_shape_job.json)
- [概念验收模板](templates/review.example.json)
- [几何测试与预览产物](../../actions/workflows/tests.yml)：成功运行后可在该次运行的 Artifacts 中查看 `l-shape-geometry-and-protocol`。

仓库中的 `examples/source_crops/02.png` 是从原图的浅蓝选区得到的二色栅格，**不是原始彩色截图**。已逐像素核对选区一致；原截图哈希和处理规则见 `examples/source_crops/PROVENANCE.json`。不以形状名称重新想象外轮廓。

模型权重、字体、凭据及用户本机环境均不随仓库提交。
