# Mac mini 16GB：L 形三层首跑

## 1. 独立工具环境

在仓库根目录执行：

```bash
conda create -n autoplan-tools python=3.12 -y
conda activate autoplan-tools
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_pilot.py --mode geometry --job examples/l_shape_job.json --out runs/l-shape-geometry-01
open runs/l-shape-geometry-01/preview.html
```

不要混用现有 IOPaint / DocRes 环境。没有 Conda 时可以使用独立 Python 3.11+ venv。中文字体优先使用本机 PingFang / STHeiti；可通过 `--font` 指向本机可用字体，本仓库不分发字体。

## 2. 本机 ComfyUI

按官方安装说明建立独立 ComfyUI 环境：<https://docs.comfy.org/installation/desktop/macos>。不要在工具环境里一次装入所有模型依赖。

另外准备 SD1.5 checkpoint 和匹配的 Canny ControlNet，核对来源、许可与模型家族。仓库不含权重、不自动下载。修改 `configs/comfy_sd15.json`，填写实际文件名和本机端口。示例文件名：

- `v1-5-pruned-emaonly.safetensors`
- `control_v11p_sd15_canny_fp16.safetensors`

默认服务器 `http://127.0.0.1:8188`；桌面版端口不同则改成本机实际端口，不暴露到公网。

```bash
python scripts/doctor.py --out runs/mac-doctor.json
```

若 autoplan-tools 没装 torch，doctor 的 torch_installed=false 不代表另一个 ComfyUI 环境没有 MPS。以本机 ComfyUI 进程及生成时保存的 server_system_stats.json 为准。

## 3. 分清预演与真实生成

```bash
python scripts/run_pilot.py --mode dry-run --job examples/l_shape_job.json --out runs/l-dry-01
python scripts/run_pilot.py --mode render --ack-concept-only --job examples/l_shape_job.json --config configs/comfy_sd15.json --out runs/l-model-01
```

两条命令使用不同目录。第一条不加载模型；第二条才提交本机生成任务。默认 512×512、batch 1、三个楼层串行、24 步、CFG 6、denoise 0.3、ControlNet strength 0.9。这是试验起点，不是 M4 16GB 的实测最优参数。

生成前卸载其他大模型，不修改内存保护阈值。当前客户端只支持 SD1.5 家族，SDXL/FLUX/Z-Image 需要另行适配，不可仅改 checkpoint 名称。

## 4. 验收

先看 generated/floor_1.png 至 floor_3.png，再看 board_model_unreviewed.png。检查墙、门、机柜和通道；最终重描边不等于原图正确。每层耗时包含排队、执行和下载，不是纯 GPU 时间。本版未自动采集 Mac 峰值内存；未测量就留空。

服务未启动、权重不存在、底图被改动、输出尺寸不匹配：停止并保存失败日志。不自动拉伸，不用云图替代。超时先查看已提交的 prompt ID，避免重复提交。再次运行换新目录。

官方接口依据：<https://docs.comfy.org/development/comfyui-server/comms_routes>。本文件不证明用户 Mac 已运行成功。
