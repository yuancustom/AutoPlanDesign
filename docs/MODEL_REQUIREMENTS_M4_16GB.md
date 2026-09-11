# P1–P3 模型需求清单｜Mac mini M4 · 16GB

版本：1.0｜资料核查：2026-09-11｜状态：**选型与准备清单，实机推理 NOT_RUN**  
适用仓库：AutoPlanDesign｜维护分支：main｜关联任务：P1-03/P1-04、P2-03/P2-05、P3-02/P3-04、BENCH-01/BENCH-02。

> 推荐先准备 **Qwen3-4B + Qwen3-VL-4B + SD1.5 + 匹配的 Canny ControlNet**。P2 可先复用 SD1.5 做带蒙版的基线，再增加专用 SD1.5 Inpainting 对比。Qwen3.5-4B、Gemma 3 4B 是优先追加的轻量视觉对照；8B、SDXL、FLUX.2 klein 放到条件试验，不一次性全装、全加载。
>
> 本文中的“适合优先测试”不等于已在你的 M4 上实测通过。文件大小不是峰值内存；模型可加载、接口可调用、建筑图效果合格、工程合规是四件不同的事。本文不下载权重、不修改 Mac 环境、不改变三个项目的代码完成状态或已登记阻塞。

## 1. 三个步骤到底需要哪类模型

| 步骤 | 模型承担的工作 | 推荐起点 | 必须由程序或人工完成的工作 |
|---|---|---|---|
| P1：带尺寸闭合轮廓 → 多层初步平面图 | 整理功能需求，提出分层/相邻关系；根据布局底稿生成图面 | Qwen3-4B；SD1.5 + Canny | SVG解析、尺寸标注、空间求解、工位/机柜准确计数、门连接、跨层核心、中文排版 |
| P2：涂抹 + 描述 → 局部修改 | 拆解修改意图；基于原图/蒙版/文字产生局部候选 | 复用Qwen3-4B；SD1.5 masked img2img；追加专用Inpainting | 画笔到原图坐标、授权蒙版、区外像素保护、版本/前后/过程记录、几何补丁及过期标记 |
| P3：确认平面图 → DXF/PDF/GLB | 从图片读出墙、门窗、房间、楼梯等，提出带证据的结构化几何候选 | Qwen3-VL-4B-Instruct | 尺度/层高确认、几何重建、真实洞口和楼梯连接、同源三格式导出、回读及人工审阅 |

以上职责来自仓库P1详细设计、P2第7–9章、P3第15–16章；链接见第12节。**不是每个项目各装一套模型，同一权重可由三个项目顺序复用。**

P3已有CURRENT几何、图像版本匹配且用户确认时，应优先复用几何，未必每次重新识图；P3独立接收图片时才需要完整识读和校准。视觉模型生成的坐标不是实测数据。

## 2. 首批需求：最小资源闭环

下表是本项目建议的采购/下载顺序，不是性能排名。GB采用发布页面约数，属于磁盘文件量。所有条目的M4端到端验收均为 **NOT_RUN**。

| ID | 模型/权重 | 建议版本与运行器 | 约下载量 | 对应项目 | M4 16GB定位 |
|---|---|---|---:|---|---|
| M01 | Qwen3-4B，纯文本语言模型 | Ollama `qwen3:4b`，核查时Q4_K_M | 2.5GB | P1规划；P2意图；Agent公开步骤摘要 | 首装，短上下文、单请求。不能直接看图。[S01] |
| M02 | Qwen3-VL-4B-Instruct，视觉语言模型 | Ollama `qwen3-vl:4b`，核对模型详情与Instruct配置，Q4_K_M | 3.3GB | P3识图主基线；P1/P2可选视觉复核 | 首装视觉模型，逐层/逐块读图，不与生图常驻。[S02] |
| M03 | Stable Diffusion 1.5 | ComfyUI；`v1-5-pruned-emaonly.safetensors`，后端使用经验证的精度 | 4.27GB | P1图面；P2遮罩基线 | 首装图面基线，从512级单图开始。该checkpoint文件大小不代表其运行精度为FP16。[S07] |
| M04 | SD1.5 Canny ControlNet | `control_v11p_sd15_canny_fp16.safetensors`，配M03 | 723MB | P1边缘约束；P2可选保留结构 | 首装控制权重。它不是独立生图模型，也不是Canny边缘提取算法本身。[S08] |
| M05 | Stable Diffusion 1.5 Inpainting | 专用inpaint checkpoint或完整Diffusers管线，选择一种；见第6节 | 发布的`sd-v1-5-inpainting.ckpt`约4.27GB | P2局部替换，与M03遮罩路线比较 | 首轮P2追加项，不是启动P1/P3的必要下载。[S09] |

### 最小组合与数量

- **先跑通软件链路：M01–M04，四项权重资源**；P2用M03的新蒙版工作流，不直接复用P1整图工作流。
- **增加P2专用重绘对照：再加M05**；不是“把普通SD1.5重命名为inpaint”。
- M01–M04发布文件量相加约10.8GB；包含上述M05 checkpoint后约15.1GB。这是文件约数加总，不包含软件、缓存、重复格式和运行结果。建议预留40–60GB可用磁盘作为首轮项目预算，并非模型官方最低要求。

极简安装也可先只装M02，分别测试其文本与视觉任务，延后M01；但须单独验证P1结构化规划和工具请求，不预设视觉模型必然完全替代纯文本模型。默认清单保留M01是为了延续现有P1方案并便于定位问题。

## 3. 后续对照模型：优先小模型，按需增加

| ID | 候选 | 精度/后端与文件量 | 项目与比较目的 | 使用条件 |
|---|---|---|---|---|
| M06 | **Qwen3.5-4B** | Ollama `qwen3.5:4b`，核查时Q4_K_M、约3.4GB | P1/P2文本候选，P3视觉候选；验证同档新架构是否减少人工修正 | **轻量对照优先**。支持文本/图片；先测图片传入、JSON约束和停止条件，不能把家族旗舰成绩套到4B。[S03] |
| M07 | **Gemma 3 4B IT** | Ollama `gemma3:4b`，Q4_K_M、约3.3GB | P3跨厂商视觉对照，也可测文本提案 | **轻量跨家族对照**。不要误下载仅文本的1B；Gemma独立许可须核对。工具调用能力另测。[S04] |
| M08 | Qwen3-8B | Ollama `qwen3:8b`，Q4_K_M、约5.2GB | 与M01做P1/P2文本规划的4B/8B对比 | **有条件试跑**，控制上下文；不能看图，不能充当独立P3识图模型。[S05] |
| M09 | Qwen3-VL-8B-Instruct | Ollama `qwen3-vl:8b`，核查时约6.1GB；执行前确认量化 | 与M02比较复杂图纸识读 | **有条件试跑**，高分辨率图像token和长上下文另占内存。[S06] |
| M10 | SDXL Base 1.0 + SDXL Canny | Base约6.94GB；对应Canny FP16约2.5GB；ComfyUI | 固定同一布局，比较P1图面 | **内存较紧的条件候选**。先做768级资源预检，再测1024级；预检图不是最终质量比较。先不加载Refiner。[S10] |
| M11 | SDXL Inpainting 0.1 | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`，完整FP16管线，容量按所选文件清单统计 | P2专用局部重绘升级对照 | **条件候选**。只处理局部工作图；模型仓库不等于一个可任意重命名的checkpoint。[S11] |
| M12 | **FLUX.2 klein 4B蒸馏版** | 首评MFLUX支持的4-bit路线；配齐文本编码器、VAE等，整体下载/峰值另核验 | P1参考图表现；P2指令编辑 | **进阶实验，不列首装**。不能只算4B流模型权重，不使用9B/base版冒充该配置。[S12][S13] |

### 为什么不直接换成最新模型？

首批保留仓库现有Qwen/SD1.5路径，是为了少改后端并形成可复现基线，不是认为旧模型普遍更好。M06、M07优先于“马上把所有模型放大到8B/20B”；通过同图同任务测试后，再决定默认配置。已安装M06且实测合格时，可评估统一文本/视觉助手，但要保留与M01/M02的基准记录。

### FLUX的关键限制

BFL模型卡包含约13GB显存的特定GPU口径，不能换算为16GB Mac完整应用保证。MFLUX维护者已实现FLUX.2量化与参考图编辑，并提供低内存/缓存相关选项；必须核对所安装版本的具体CLI支持。[S12][S13]

其参考图编辑接口**不自动等于原生硬蒙版接口**。P2仍需“授权区裁切→编辑→按原分辨率蒙版合成”，分别检查raw与final。没有本机资源实测前，不承诺1024分辨率、生成秒数或稳定批处理。内存不足时停止、登记，再采用新配置重试，不改系统内存保护。

## 4. 可选专项能力，以及不必下载的模型

| 项目 | 结论 | 原因 |
|---|---|---|
| LaMa / Big-LaMa | 仅在P2大量需要消除旧符号/补背景时追加；先评估CPU小图路径 | LaMa是图像补全模型，不是Llama语言模型。不是“按文字新增指定数量机柜”的替代品；作者有CPU推理入口，不等于其旧依赖已在M4验收。[S14] |
| 点击分割/SAM类 | 手工涂抹第一版不必安装；自动选区独立需求出现后再选型 | 浏览器画笔、蒙版生成不需要神经网络。通用分割也不能自动证明建筑墙体语义 |
| OCR | 先用原SVG/PDF可提取内容、视觉读图与局部复核；专用OCR延后 | 仅在文字读取成为实测瓶颈后增加，不能用OCR重建SVG已有几何，也不能让识别数字覆盖尺度事实 |
| Embedding / Reranker | 当前三步骤无强制需求 | Skill和少量项目配置可以直接读取；检索模型不负责排房、重绘或CAD导出 |
| 通用图生三维模型 | **不作为P3主线需求** | 我们要的是稳定ID的墙/门窗/楼梯、真实尺度和同源二维图纸，不是一个仅看起来像建筑的网格 |
| 训练/LoRA | 首轮只推理，不纳入M4训练准备 | 先证明数据、约束和推理流程；专用建筑LoRA应有授权数据和独立资源/实验计划 |

**不建议在这台16GB机器上首装：** Qwen-Image-Edit-2511的20B级图像编辑路线、Qwen3-VL-32B、FLUX.1 schnell 12B，以及未明确支持当前Mac后端的复杂多控制插件。不是断言量化后绝对不能运行，而是它们不适合作为低风险起点。MoE激活参数量小也不能当作总权重很小。[S15]

## 5. 每个项目的执行组合和接口能力要求

### P1：轮廓与参数到三层图片

```text
程序解析SVG/校尺/标注
→ M01（或M06）提出功能关系JSON
→ 确定性布局求解与几何、数量校验
→ 每层无字guide + mask + edges
→ M03+M04；对照M10/M12
→ 程序中文/精确对象层 + 原始模型图复核
```

SVG尺寸标尺、机柜/工位计数、Shapely/CP-SAT及工程轮廓渲染**不需要另购AI模型**。展示公开决策摘要、实际工具步骤和证据即可，不把隐藏思维链作为功能依赖。三层分别生成后拼版，不同时占用三份模型管线。[R1]

### P2：同一原图、同一选区与同一指令

第一条线复用M03：`image + mask + prompt → masked img2img`。第二条线使用M05专用模型：`image + mask + prompt → inpainting conditioning`。ComfyUI维护者提供的inpaint例子支持专用与非专用模型，但两者条件管线不能视为完全相同。[S16]

M01做中文指令拆解、生成SD用的受控英文表现提示；业务原话和结构化变更不能被翻译丢弃。旧Canny若保留要删除机柜的边缘，会和指令冲突：控制图从目标几何/应保留边缘产生，而不是总对原图做一次Canny。[R2]

后端必须声明：是否支持原生mask、mask白黑含义、支持精度/尺寸、ControlNet家族、是否返回raw、取消行为。保存before/mask/request/raw_after/final_after/差异/事件，不覆盖历史。final区外像素相同是程序合成保证，不是模型能力得分。[R2]

### P3：多层图片到同源几何和三格式

```text
逐层原图与参数台账
→ M02 / M06 / M07提出对象、关系、证据与不确定项
→ 尺度确认 + 几何候选校验/人工纠正
→ BuildingIR
→ 同一几何导出DXF（mm）、PDF、GLB（m）
→ 回读、实际看图与用户审阅
```

模型要真实接收图像，不得把另一个模型写出的摘要喂给纯文本模型后，宣称它独立完成识图。精细图纸宜先看全层建立对应，再顺序读局部块并映射回统一坐标；裁块不能遗失墙连接和楼层关系。[R3]

ezdxf、Trimesh、平面几何/PDF工具是软件库，不是要下载权重的“建模大模型”。网页查看器/BIMFACE同样不是推理模型。三维成果必须来自实际几何；P3的图像理解能力不能由P1的生图模型代替。[R3]

## 6. 可以实际准备的文件与命令

### 6.1 Ollama：先原生运行，不先套Docker

建议在M4原生macOS运行Ollama；其官方FAQ说明macOS Docker Desktop路线没有该GPU直通加速。Ollama具备结构化输出接口，但格式约束仍需业务校验。[S17][S18]

安装兼容这些模型的当前版本后，先只执行：

```bash
ollama --version
ollama pull qwen3:4b
ollama pull qwen3-vl:4b
ollama list
ollama show qwen3:4b
ollama show qwen3-vl:4b
```

按实验目的选装，不要求全执行：

```bash
# 轻量多模态与跨家族对照
ollama pull qwen3.5:4b
ollama pull gemma3:4b

# 较大同家族对照：4B验证之后再准备
ollama pull qwen3:8b
ollama pull qwen3-vl:8b
```

不用不带大小的默认标签或`:latest`；下载后保存完整digest/实际量化和上下文配置，后续同名标签更新按新配置登记。原始作者模型身份和Ollama打包标识分别记录，不能从名称猜测Instruct/Thinking、视觉组件或量化细节。[S01–S06]

### 6.2 ComfyUI：明确模型目录及真实文件名

使用官方macOS本地安装路线。ComfyUI是运行器，不是模型，Comfy Cloud与Partner云节点不属于本清单的本地路径。[S19]

```text
ComfyUI/models/checkpoints/
  v1-5-pruned-emaonly.safetensors        # M03
  sd-v1-5-inpainting.ckpt               # M05，可选；仅使用已核查来源
  sd_xl_base_1.0.safetensors             # M10，第二批

ComfyUI/models/controlnet/
  control_v11p_sd15_canny_fp16.safetensors  # M04
  sdxl_canny_fp16.safetensors              # M10的本地重命名示例
```

| 资源 | 获取位置 | 注意事项 |
|---|---|---|
| M03基础checkpoint | [SD1.5发布镜像文件列表](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/tree/main) | 只选4.27GB的emaonly safetensors，不必下载整个仓库的重复权重 |
| M04控制权重 | [ComfyUI维护者FP16转换文件列表](https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/tree/main) | 精确选Canny文件；不是Lineart、Tile或Control-LoRA；作者原模型见S08 |
| M05专用inpaint | [SD1.5 Inpainting文件列表](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting/tree/main) | 核查到的单文件是`sd-v1-5-inpainting.ckpt`；不杜撰同名safetensors。该分发入口自述为镜像，不冒充原作者账号 |
| M10基础与控制 | [SDXL Base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/tree/main) / [SDXL Canny](https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/tree/main) | Canny原文件`diffusion_pytorch_model.fp16.safetensors`；改成本地明确名称后仍保存原名/来源/hash |
| M11专用inpaint | [Diffusers SDXL Inpainting](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1) | 发布为组件目录的管线要配齐UNet、两个文本编码器、tokenizer、VAE及配置；不要只下载UNet放进checkpoints并声称完整 |

`.ckpt`可能包含pickle序列化内容，不能因“模型文件”就当任意来源可信。M05先核查来源/完整性并使用支持安全权重加载的运行器；不得为了载入陌生文件关闭安全限制。来源或兼容性没核实，就先留在M03带蒙版路线。可信safetensors转换制品需另行核验和登记，不在本轮编造下载地址。

### 6.3 后端与精度不能混用

Ollama的GGUF、ComfyUI的checkpoint、Diffusers组件目录、MLX量化目录不是可以互相改后缀替换的文件。基础完整checkpoint可包含文本编码器和VAE；拆分管线必须另外补齐，是否内置由实际模型格式确认。

Mac使用Metal/MPS或MLX，不照抄NVIDIA教程的CUDA安装、xFormers或NVFP4加速假设。SD可先测FP16计算，VAE精度按后端需要配置；出现黑图/NaN时记录失败并另建配置验证，不随意改全局环境。Diffusers官方有MPS说明，但支持MPS不能推导为所有pipeline/节点均已在M4通过。[S20]

## 7. M4 16GB资源策略

以下是**项目初始配置建议**，不是实测最优值或官方最低配置。

| 项目 | 起步设置 | 升级条件 |
|---|---|---|
| 语言/视觉上下文 | 先4096，确需更多证据时尝试8192；输入图像token与输出均计入预算 | 实测内存稳定；内容放不下时分任务，不静默截断图纸/规则 |
| 视觉输入 | 一次一层概览，必要时逐块补看；全图和局部坐标可追溯 | 通过清晰度与对象漏检检查后调整；不能缩小到尺寸文字不可读 |
| SD1.5 | batch=1，512级，先一个ControlNet | 先完成单层raw检查，再测试768级 |
| P2工作图 | 裁出授权区及必要上下文，从512级开始 | 不裁掉理解修改所必需的上下文；有效修改区独立保存 |
| SDXL | 单管线，先768级资源预检，再测试1024级 | 768级只是资源配置；不同分辨率评分分组，不据此宣布SDXL差于SD1.5 |
| FLUX.2 klein | 4B蒸馏、兼容4-bit、单参考图、小尺寸首测 | 先确认整个pipeline资源和低内存选项；不承诺1024批量 |
| 三项目调度 | 共用一个推理资源锁、串行执行 | 前端可比较多模型结果，但不同时驻留多个大模型 |

Ollama设置仅控制Ollama自身，不会替ComfyUI/MFLUX释放内存。调度器必须跨后端安排生命周期。语言/视觉提案保存后先卸载，再启动图面或较重网格处理；模型切换前后记录实际驻留与swap。[S17]

可选的Ollama本机设置（会影响该应用，执行前确认其他任务不受影响；设置后完全退出并重启Ollama）：

```bash
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
launchctl setenv OLLAMA_NUM_PARALLEL 1
launchctl setenv OLLAMA_NO_CLOUD 1
```

完成当前阶段后释放**实际正在使用的**模型，例如：

```bash
ollama stop qwen3:4b
ollama stop qwen3-vl:4b
ollama ps
```

API也可用`keep_alive: 0`。上述环境变量、本地关闭云功能和释放方式均有官方说明。[S17]

内存压力持续异常、swap快速增加或出现OOM，应停止/标记该attempt，并按已登记的小输入配置重试。不要设置`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0`来取消保护，不自动转用云模型，不把降级运行混进原配置成绩。没有实机证据，本清单不提供“每张多少秒”“实际占几GB”的数字。

## 8. 同源多模型测试最小矩阵

保留T0：确定性几何/蒙版/导出器测试。T1以4B量化与SD1.5为主；T2选8B、SDXL、FLUX条件配置；T3大模型留在额外批准硬件，不进入M4首装。

| 试验 | 固定内容 | 首轮变量 | 看什么 |
|---|---|---|---|
| P1规划 | SVG几何、尺度、工位/机柜/房间参数、solver、预算 | M01 vs M06；之后M08 | 数量保持、方案可行率、拓扑与人工修正量 |
| P1图面 | 同一个通过检查的layout hash、楼层、控制图生成规则 | M03+M04 vs M10；之后M12 | raw外壳/假墙/符号漂移、可读性；final独立评价 |
| P2编辑 | 同一before revision、原分辨率蒙版、文字、修改分类 | M03 masked img2img vs M05；之后M11/M12 | 目标完成率、raw区外泄漏、final区外保护、几何同步 |
| P3识图 | 同层原图/局部块、尺寸事实、Schema、原Skill/工具/导出器 | M02 vs M06 vs M07；之后M09 | 墙门窗/梯及宿主识别、尺度与标高、三格式几何一致性 |

P1只更换图面模型的试验必须固定布局；各模型分别重排房间的试验是整链路试验，不能归因于画图能力。P3人工黄金几何只用于评分/T0，不泄露给识图模型。[R1–R3]

先单案例冒烟，再按三个种子/重复试验保存所有结果。3个图面配置×3次×3层为27次单层任务；并发仍为1。规划调用覆盖整栋时不能重复再乘楼层数。温度/种子/处理器/量化与输入变换均记录；不同家族相同seed不意味着随机性等价。

每次记录：输入及蒙版hash、模型来源/revision/量化/组件hash、runtime/节点版本、Skill/提示模板、seed、分辨率、context/token预算、raw/final、公开步骤、冷启动/推理耗时、内存/swap、错误、人工审查与批准引用。失败和OOM不能被删掉；NOT_RUN不是低分也不是PASS。

## 9. 能力探测与验收：下载完不等于开发完

建议模型配置生命周期：

```text
CANDIDATE → DOWNLOADED → LOAD_VERIFIED → CONTRACT_VERIFIED
→ MODEL_EXECUTED → QUALITY_REVIEWED → APPROVED_PROFILE
```

这些是拟议状态，不是当前仓库已实现的调度功能；不直接修改现行合同枚举。任何阶段可BLOCKED/FAILED，推荐顺序不自动构成运行授权或设计审批。

| 门禁 | 必须实际验证 |
|---|---|
| G1身份和资源 | 可读权重、模型家族/量化/组件齐全、来源hash、后端支持；真实M4/16GB及系统版本 |
| G2文本接口 | 严格JSON、数量不被改写、最大输出/停止；工具请求只映射白名单，不执行任意代码 |
| G3视觉接口 | 确实发送图像；不同楼层/局部块能区分；不会用纯文本调用冒充读图 |
| G4编辑接口 | 黑白蒙版方向、缩放回投、原生inpaint与普通masked流程区别、raw留存 |
| G5建筑质量 | 核心/尺度/门窗/设备数量实际核对；不是只测文件存在 |
| G6集成与本地性 | 版本/hash/STALE阻断、取消/恢复、权重下载后离线重放、无云fallback |

现有P1原型测试、历史几何测试和工作流dry-run不替代以上模型实测。P3之前登记的原Skill文件导入阻塞也不会因“已下载视觉模型”自动消失。[R1–R3]

## 10. 开发者落实到代码的需求

**共用资产，独立适配，不互相import项目内部模块。**每个后端profile需声明支持的任务、输入模态、原生mask、ControlNet家族、量化/精度、最大输入、取消方式与raw输出；UI仅开放真正通过兼容性探测的能力。

P1：实现规划JSON适配和受控渲染；P2：实现独立蒙版条件、裁切回贴和不可变记录；P3：实现视觉到BuildingIR候选、证据绑定和确定性导出。共同队列安排M4资源，但不得把三个项目的状态/审批混在一起。

本文为三项目统一的**准备优先级**，补充原各项目的候选清单：将P1的可选视觉模型提升为P3首批需求；P2先复用P1权重再加inpaint；对P3已有Qwen3.5/Gemma候选补上具体运行标识。旧候选继续保留，不自动迁移`benchmarks/models.json`或声称新适配已实现。

## 11. 用户准备顺序

| 顺序 | 准备内容 | 完成后能支持的开发验证 |
|---|---|---|
| A | 原生Ollama + M01/M02 | P1/P2结构化意图；P3图像识读接口 |
| B | 本地ComfyUI + M03/M04 | P1受控图面；P2带蒙版基线 |
| C | 经来源核验的M05 | P2专用重绘对照 |
| D | 优先M06/M07，之后按需M08/M09 | 文本/视觉跨模型与大小分层比较 |
| E | M10/M11；再评估M12 | 高资源图面/编辑实验；不作为开始开发前置条件 |

只准备A–C就可以开始三项目的首轮模型集成开发；是否产出合格方案，仍取决于待开发算法/接口和实测，不能仅靠模型安装完成。无需准备付费云API作为自动后备。

## 12. 来源、文件位置与维护

### 仓库设计依据

本次读取基线提交：`b67b7e1a1406473340a9aba0a91ba65d5ef41833`。本文件不改写其代码、P2/P3原型或未解决阻塞。

- [R1：P1开发设计](../projects/outline-plan/docs/P1_DEVELOPMENT_SPEC.md) / [原模型准备清单](../projects/outline-plan/docs/MODELS_PREPARATION.md)。
- [R2：P2详细设计，第7–9章](../projects/region-edit/docs/DETAILED_DESIGN_V1.md)。
- [R3：P3开发设计，第15–16章](../projects/plan-delivery/docs/P3_DEVELOPMENT_v1.0.md)。
- [全局总控](../CONTROL.md) / [文档与代码双交付](../governance/DOC_CODE_DELIVERY.md) / [实验协议](../benchmarks/PROTOCOL.md)。

### 模型发布者、运行器维护者资料

核查日期2026-09-11。模型/运行器页面支持身份与接口事实；推荐级别、下载先后、起步参数和容量预算是本项目选择，不是官方M4实测结论。mutable标签、许可和后端支持须在安装时重新核对。

- **S01** [Ollama Qwen3-4B：标签、量化和文件量](https://ollama.com/library/qwen3:4b)。
- **S02** [Ollama Qwen3-VL-4B](https://ollama.com/library/qwen3-vl:4b) / [Qwen原作者4B-Instruct模型](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)。
- **S03** [Qwen3.5-4B作者模型卡](https://huggingface.co/Qwen/Qwen3.5-4B) / [Ollama 4B打包](https://ollama.com/library/qwen3.5:4b)。
- **S04** [Ollama Gemma 3 4B：视觉版本和许可](https://ollama.com/library/gemma3:4b)。
- **S05** [Ollama Qwen3-8B](https://ollama.com/library/qwen3:8b)。
- **S06** [Ollama Qwen3-VL-8B](https://ollama.com/library/qwen3-vl:8b)。
- **S07** [SD1.5镜像模型卡](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) / [文件列表](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/tree/main)。
- **S08** [ControlNet原作者SD1.5 Canny](https://huggingface.co/lllyasviel/control_v11p_sd15_canny) / [ComfyUI维护者FP16转换权重](https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/tree/main)。
- **S09** [SD1.5 Inpainting维护镜像](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting) / [实际文件列表](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting/tree/main)。
- **S10** [SDXL Base作者文件](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/tree/main) / [Diffusers SDXL Canny文件](https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/tree/main) / [ComfyUI SDXL示例](https://comfyanonymous.github.io/ComfyUI_examples/sdxl/)。
- **S11** [Diffusers团队SDXL Inpainting 0.1](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1)。
- **S12** [BFL FLUX.2 klein 4B蒸馏版](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)。
- **S13** [MFLUX项目](https://github.com/mflux-community/mflux) / [FLUX.2适配说明](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/flux2/README.md) / [低内存等公共选项](https://github.com/mflux-community/mflux/blob/main/src/mflux/models/common/README.md)。
- **S14** [LaMa作者项目：预训练模型与CPU推理说明](https://github.com/advimman/lama)。
- **S15** [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) / [FLUX.1 schnell 12B](https://huggingface.co/black-forest-labs/FLUX.1-schnell) / [Ollama Qwen3-VL各规模文件量](https://ollama.com/library/qwen3-vl)。
- **S16** [ComfyUI维护者Inpainting示例](https://comfyanonymous.github.io/ComfyUI_examples/inpaint/)。
- **S17** [Ollama FAQ：本地、Mac环境变量、Docker限制、模型驻留/并发/释放](https://docs.ollama.com/faq)。
- **S18** [Ollama结构化输出](https://docs.ollama.com/capabilities/structured-outputs)。
- **S19** [ComfyUI官方macOS本地安装](https://docs.comfy.org/installation/desktop/macos)。
- **S20** [Diffusers官方MPS说明](https://huggingface.co/docs/diffusers/optimization/mps)。

维护规则：先真实测试一个模型profile，再更新推荐与登记；模型下载量、来源revision或能力改变时更新本文日期和对应profile。不得把“准备完成”改写为“P1–P3已经全部开发完成”。
