# P1 模型与环境准备清单

核对日期：2026-09-11。目标是Apple Silicon Mac mini 16GB；这是建议的实验配置，不是这台机器的速度/内存实测。下载权重不等于P1适配已实现。所有模型实验仍为NOT_RUN。

## 1. 首先准备什么

最小闭环：确定性SVG/几何工具＋Qwen3-4B（功能规划）＋SD1.5及匹配Canny（图面基线）。同一SVG先比较规划模型时，再加Qwen3-8B；比较图面时再加SDXL及匹配Canny。没有模型也应能保存带尺寸工程轮廓、编辑参数和输出确定性布局测试图。

| 优先级 | 模型/配置 | 准备内容 | 用途与边界 |
|---|---|---|---|
| 首批 | Qwen3-4B | Ollama `qwen3:4b`，当前标签约2.5GB、Q4_K_M | 从已解析轮廓/参数生成结构化功能关系和候选策略；不负责SVG尺度或精确排房 |
| 首批 | SD1.5＋ControlNet Canny | `v1-5-pruned-emaonly.safetensors`约4.27GB；`control_v11p_sd15_canny_fp16.safetensors`约723MB | 512级低成本控制链路基线；不是建筑专用模型，也不是保证最漂亮的模型 |
| 第二批 | Qwen3-8B | Ollama `qwen3:8b`，约5.2GB、Q4_K_M | 与4B固定输入/求解器比较规划质量，单独加载 |
| 第二批 | SDXL Base 1.0＋SDXL Canny | `sd_xl_base_1.0.safetensors`约6.94GB；SDXL Canny的`diffusion_pytorch_model.fp16.safetensors`约2.5GB，入库时可明确重命名 | 同一布局下的更高分辨率候选；不同时加Refiner，不混用SD1.5 ControlNet |
| 可选 | Qwen3-VL-4B-Instruct | Ollama `qwen3-vl:4b`，约3.3GB；确认tag/digest对应Instruct版本 | 图面复核或输入图片的辅助理解；SVG可直接解析，不必让VLM先OCR再猜尺寸 |
| 后续试验 | FLUX.2 klein 4B（蒸馏版） | MFLUX或ComfyUI兼容量化包及配套文本编码器/VAE，建议从4-bit配置评估 | 布局参考图编辑路线；不与base-4B混淆，不套SD1.5采样/ControlNet配置 |

文件大小来自发布/运行器页面，仅是磁盘下载量；不是推理峰值内存。不要下载整个SD仓库的所有重复格式/训练权重，只取选定checkpoint和控制模型。SD1.5分发仓库是原项目镜像；ControlNet半精度为comfyanonymous转换版本，分别记录来源，不称它们全部是原作者原始权重。

FLUX官方提及约13GB独立GPU显存是特定环境数据，不是16GB Mac一定可运行的保证。4B是流模型规模，不表示文本编码器、VAE与其他资源免费。先通过本机最小推理与接口烟雾测试，未适配时前端禁用其生成按钮。

## 2. 在本地准备语言模型

安装Ollama后在Mac终端运行（本次不在用户机器代执行）：

```bash
ollama pull qwen3:4b
# 要做规划能力4B/8B对比时准备：
ollama pull qwen3:8b
# 仅在需要看图复核时准备：
ollama pull qwen3-vl:4b
ollama list
ollama show qwen3:4b
```

保存版本、完整digest、模型细节及量化信息；mutable tag在后续更新前需生成新模型配置revision。Ollama支持JSON Schema约束输出，但仍须做后端几何/数量检查。上下文起步设4096~8192为资源试验值，不因模型宣传大窗口直接开启极长上下文。

生图前卸载语言模型，如 `ollama stop qwen3:4b`，或接口请求使用keep_alive=0。实际API只使用本机服务；不要选择cloud标签或云fallback。

## 3. 准备图面运行器

首选ComfyUI作为SD1.5/SDXL的自动化入口。Apple Silicon可使用官方macOS安装路线；API后端记录实际端口，不能假定每个Desktop安装都为8188。为新P1使用独立环境，不修改IOPaint/DocRes现有环境。

模型位置约定：

```text
ComfyUI/models/checkpoints/
  v1-5-pruned-emaonly.safetensors
  sd_xl_base_1.0.safetensors             # 第二批
ComfyUI/models/controlnet/
  control_v11p_sd15_canny_fp16.safetensors
  sdxl_canny_fp16.safetensors           # 来自SDXL Canny fp16文件，记录原名/哈希
```

校验checkpoint、控制模型家族、VAE、文本编码器及节点存在后才标READY。单文件ComfyUI与Diffusers目录结构不同，不把一个目录模型的某一文件直接当完整pipeline。FLUX量化/文本编码器加载由专用profile检查，先不必下载。

准备后用`shasum -a 256 <文件>`保存本地文件hash。先核对许可、来源与运行器兼容；本准备包不含权重、字体或凭据。建议为最小组合及环境/缓存预留约20~30GB磁盘，为全部可选组合另预留空间；这是项目容量预算，不是模型官方最低配置。

## 4. 首轮测试组合

A0：规则分配＋固定求解器＋SVG程序出图（无模型）。
A1/A2：Qwen3-4B / Qwen3-8B＋同一求解器＋SVG程序出图，比较规划。
B1/B2：同一个layout_sha＋SD1.5 Canny / SDXL Canny，比较图面。
B3：同一layout_sha＋FLUX.2 klein参考编辑，单独标注适配与分辨率差异。

只选择实际就绪的配置，16GB单次一层、一个worker、batch=1；分辨率从512级开始试验，高分辨率单列配置。OOM/不支持节点/无法加载都是记录，不伪造成功图。模型数量、候选数、种子和楼层会相乘，前端先展示真实任务数量。

首批模型与已有工具不保证生成质量；第一轮验收必须看真实模型原图、确定性几何和数量对照。模型可能改变墙和家具数量，因此正式图的参数符号和中文字从几何数据绘制，原图评分单独计算。

## 5. 技术依据（官方发布者/维护者资料）

模型标识、文件和接口于上述日期核对；页面的宣传成绩不直接写成本项目成绩。

- Qwen3 Ollama版本/量化/磁盘大小：`https://ollama.com/library/qwen3:4b`、`https://ollama.com/library/qwen3:8b`
- VLM：`https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct`、`https://ollama.com/library/qwen3-vl:4b`
- Ollama结构化输出及卸载：`https://docs.ollama.com/capabilities/structured-outputs`、`https://docs.ollama.com/faq`
- SD1.5分发文件与镜像声明：`https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5`
- ControlNet原作者：`https://huggingface.co/lllyasviel/control_v11p_sd15_canny`
- 半精度转换：`https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/tree/main`
- SDXL：`https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0`、`https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0`
- FLUX：`https://huggingface.co/black-forest-labs/FLUX.2-klein-4B`、`https://github.com/mflux-community/mflux`
- ComfyUI：`https://docs.comfy.org/installation/desktop/macos`、`https://docs.comfy.org/development/comfyui-server/comms_routes`
- SVG坐标与渲染：`https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/viewBox`、`https://github.com/linebender/resvg`
- 几何与求解器：`https://shapely.readthedocs.io/en/stable/manual.html`、`https://developers.google.com/optimization/cp/cp_solver`
- 长时任务不放普通后台回调的依据：`https://fastapi.tiangolo.com/tutorial/background-tasks/`
