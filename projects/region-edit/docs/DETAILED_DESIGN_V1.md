# AutoPlanDesign · P2 区域重绘详细设计

**版本：v1.0 / 设计评审稿（仓库同步版）**  
**日期：2026-09-11**  
**项目：`projects/region-edit`**  
**目标环境：用户的 Mac mini 16GB；实际芯片、macOS、后端版本在部署时登记**

> 目标：用户打开一张已有平面图，用鼠标涂抹区域并输入文字，生成局部修改候选；未授权区域保持不变，修改前、修改后和公开执行过程可追溯；与 P1、P3 的版本和几何状态保持一致。
>
> 本轮交付是调研及详细设计，不是已实现的软件、已完成的模型性能测试或工程审查。初稿仅在对话中交付；仓库同步只新增本设计文档和 README 入口，不修改业务实现、合同或任务完成状态。没有对用户原图执行 AI 重绘。示例选区是人工设置的设计说明，不是自动识别结果。

## 阅读导航

01 决策摘要与开发边界；02 仓库现状与合同缺口；03 开源案例调研；04 用户图片试点；05 产品交互；06 蒙版与坐标；07 后端重绘算法；08 本地模型分层；09 图片、几何与 P3；10 修改记录与恢复；11 API 与数据；12 代码组织；13 评测与验收；14 开发任务；15 风险与决策；16 首轮验收脚本；17 示例请求与提示词；18 来源。

## 01｜决策摘要与开发边界

### 1.1 核心结论

**这个功能可以开发。建议自建轻量的平面图编辑器，复用本机 ComfyUI 的推理能力；不要把某个通用 AI 绘图软件整体改造成建筑系统，也不要让一个大模型包办选择、编辑、尺寸和历史记录。**

推荐方案分为四个职责层：

| 层 | 推荐方案 | 职责与边界 |
|---|---|---|
| 编辑器 | React + TypeScript + Konva，作为待批准 ADR | 画笔、擦除、缩放、选区、保护区、比较和接受/拒绝；不负责模型推理 |
| 业务服务 | Python + FastAPI，沿用 P2 独立包边界 | 来源校验、任务队列、裁切合成、几何状态、版本和事件 |
| 存储 | SQLite + 本机内容寻址文件目录 | 元数据事务和不可变文件；首期不需要 Redis、云对象存储或分布式集群 |
| 模型后端 | 优先本地 ComfyUI；后续再适配其他本地后端 | 使用真正的图像＋蒙版条件；batch=1、并发=1，不自动转云 |

Konva 官方有可保存笔画、支持画笔/擦除及撤销的 React 示例，也有缩放嵌套下鼠标坐标逆变换示例；这些能作为画布实现依据，但不是本项目已完成的 UI。[S08][S09]

### 1.2 产品承诺分级

**能够通过程序严格保障的部分：** 原图和历史不覆盖、坐标变换可追踪、蒙版权限固定、最终输出在授权区外的解码像素完全一致、生成失败不改当前版本、过期几何不交给 P3。

**只能通过生成结果和复核评估的部分：** 改动是否符合文字、机柜画得是否像平面符号、接缝是否自然、房间内部是否出现假墙。通用模型不能凭提示词保证机柜数量、门宽或结构合理。

**必须走结构化路径的部分：** “恰好六个机柜”“移动门洞”“办公室改机房”“移动楼梯”。涉及对象数量、用途、几何或跨层影响时，生成对象/语义补丁并复核；不能将这些改动统称为美化。

### 1.3 首期范围

首期完成：单张单层图导入、画笔和橡皮、矩形/多边形辅助选择、蒙版确认、文字指令、单候选生成、前后比较、原图/结果/过程存储、接受/拒绝、回滚、断线恢复，以及 IMAGE_ONLY 状态展示。

首期不完成：任意图片自动恢复准确建筑几何、全楼自动改造、多人实时协同、无审批调整楼梯或外壳、主发电设备工艺设计、直接输出施工图。框架并不妨碍后续增加这些能力，但不会提前标记为已支持。

## 02｜与仓库当前状态对齐

### 2.1 本轮实际读取的内容

本设计读取了 `main` 上的 `CONTROL.md`、`projects/region-edit/README.md`、`contracts/pipeline.schema.json`、`governance/backlog.json`，以及 P1 冻结基线的 `scripts/comfy_client.py`。相关来源见 [R01]—[R05]。

| 当前事实 | 对 P2 的影响 |
|---|---|
| P2 README 明确目前只有骨架和协议，没有可用涂抹 UI、模型编辑或长期审计 | 本文所有 UI、编辑服务、版本存储均是待实现，而不是现成功能 |
| P1 基线图为 `VAEEncode → KSampler`，额外接 Canny；没有用户编辑 mask 输入 | 可借用网络检查与执行留痕思路，不能只给旧工作流加提示词就称为局部重绘 |
| `EditRequest` 已有 `appearance/layout`、base/head、蒙版、变换与审批字段 | 保留这些枚举和语义；扩展字段必须经合同版本评审 |
| `PlanRevision` 0.1.0 强制 `world_unit=m` 和 3×3 `pixel_to_world` | 外部未知尺寸图片不能伪造米制单位或身份矩阵通过合同 |
| 总控要求原始模型图与最终合成图分开、区外最终像素差为零 | 模型图只作为候选；业务服务负责权限合成及逐像素检查 |
| `P2-01` READY，`P2-02`—`P2-05` TODO | 本文拆分子任务，不自行更新原台账或将设计标为 DONE |

### 2.2 必须先解决的合同缺口

**推荐：P2 内部新增 `ImageEditSession`，承载未知尺度的图片导入；跨项目的 0.1.0 合同先不暗改。**

外部图片可以先编辑，使用像素坐标，`geometry_status=IMAGE_ONLY`、`scale_status=UNKNOWN`、`pixel_to_world=null`。它还不是一份合法的 0.1.0 米制 `PlanRevision`，不送入 P3。取得尺度依据及经确认的几何后，再由显式适配器转换。

以后确实需要三项目统一支持未知尺度，提交 `contracts` 0.2.0 变更提案：按输入状态允许未知单位与空变换，并补齐迁移/负例。不得往当前 `additionalProperties=false` 的对象随意塞新字段。

现有 `EditRequest` 是已有 PlanRevision 的跨项目请求。IMAGE_ONLY 路径使用 P2 内部 `ImageEditCommand`，两者映射到同一个内部执行计划。不能伪造不存在的 `base_revision_id` 冒充 P1 产物。

## 03｜网络上别人怎么做：可借鉴的开源实现

### 3.1 调研结论表

下表区分“已有工具事实”与“本项目取舍”。调研日期为 2026-09-11；安装时还需固定具体版本和依赖。

| 项目 | 核验到的能力 | P2 借鉴点 | 不直接等同于我们的能力 |
|---|---|---|---|
| InvokeAI | 本地 React Web UI、统一画布、画笔、局部/扩图、工作流、图库与参数回忆 | 选区→生成→暂存候选→接受的交互；把生成结果与当前画布分开 | 通用图库和工作流元数据不是建筑版本、几何同步与审批链。[S01][S02] |
| Krita AI Diffusion | Krita 选区填充、ControlNet/控制图层、区域提示、队列、历史；使用 ComfyUI 后端 | 只生成选区、保留上下文、调节变化强度，以及结果可选择应用 | 它是桌面绘画插件，不直接提供 P1/P2/P3 业务接口和几何审批。[S03][S04] |
| ComfyUI | Mask Editor 可鼠标绘制蒙版；有 inpaint 节点、API 和节点工作流 | 作为可固定版本的本机推理引擎和调试工作台 | 节点编辑器不是最终给建筑用户使用的产品界面。[S05][S06][S07] |
| IOPaint | Web 编辑、消除模型、提示词重绘模型、Apple Silicon 支持 | 简单上传—涂抹—执行的轻交互和消除任务路由 | 仓库明确于 2025-08-13 归档，只作为参考或受控验证工具，不作为持续维护主干。[S10] |
| ComfyUI Inpaint CropAndStitch | 围绕蒙版裁切上下文、缩放、推理后回贴；说明了选区外不经过 VAE 的做法 | 裁切/上下文/回贴的算法分层 | 自动 grow/blur/fill holes 可能改变编辑范围；P2 必须自己掌握最终授权蒙版。[S11] |

### 3.2 具体怎么借鉴

**产品交互参考 InvokeAI，精细选区参考 Krita，推理使用 ComfyUI，裁切与最终合成由 P2 掌握。** 这比完全复制一套绘图软件更利于 P1/P3 集成。

Krita 文档明确区分选区和上下文：模型会处理上下文，即使它不被修改；上下文越大，资源代价也会增加。P2 应展示这两种区域，而不是只画一个半透明框。[S04]

CropAndStitch 很适合验证裁切思路，但默认参数不是我们的权限制度。任何自定义节点导致的 mask 扩张，必须在预览中显式呈现，或者只限于模型工作区，不能自动扩大最终写回范围。[S11]

**代码与许可处理：** 这里只复用架构思路和公开接口。Krita AI Diffusion 与 CropAndStitch 仓库标注 GPL-3.0，InvokeAI/IOPaint 主仓库标注 Apache-2.0；直接引入代码前登记 LICENSE、版权声明、具体文件及分发方式，再做许可核对。模型权重、插件和应用各自登记，不能只看主仓库许可证就推断整套依赖许可。[S01][S03][S10][S11]

### 3.3 为什么“普通局部重绘”还不够

照片里邻近颜色有些变化可能还能接受，平面图里一条细线的变化却可能变成新墙或堵住门洞。因此 P2 除了生成，还必须控制：实体保护、选区外零改动、中文标注、结构化数量、几何状态和修改谱系。这些是本项目的设计要求，不是声称上述工具均能完成。

## 04｜用用户这张平面图定义首个试点

### 4.1 输入事实与不能推断的内容

附件尺寸为 **768×512 像素**。图中可见楼梯 A/B、公共走廊、机柜区、辅助机房、办公室、检修间、设备缓冲、配电辅助、管井及卫生空间文字。这些来自对上传图片的直接观察。[U01]

本轮未取得与该图片绑定的几何 JSON、真实尺寸、楼层号或北向。不能沿用前文其他 H 形示例的 50m×30m、层高或面积；也不能把图中可见名称当作已经核验的建筑功能规范。导入状态应为 IMAGE_ONLY。

**私有附件图 1：用户输入原图。** 原图保留在本次对话的文档包中，不随公共仓库提交。

*图 1：用户上传的原图，未重绘。用途是 P2 私有开发样例，不能自动上传公共仓库。*

### 4.2 首个区域和说明图

选择下排中左的“机柜区”。示意授权区域使用原图坐标 `[232,370,374,476)`，房名保护矩形为 `[267,407,340,434)`；上下文矩形为 `[210,280,398,496)`。坐标为设计示例，不是自动检测或测量成果，真正执行前用户可修正。

**私有附件图 2：编辑范围、保护范围和只读上下文。** 说明图保留在本次对话的文档包中；本仓库以本节像素坐标和文字描述说明范围，不上传用户图纸。

*图 2：绿色是示例允许修改区；橙框是示例房名保护；蓝框是可供模型理解但不等于允许改写的上下文。图 2 只添加说明覆盖层，不表示模型已编辑成功。*

### 4.3 首轮四个任务

| ID | 用户操作与文字示例 | 处理方式 | 通过条件 |
|---|---|---|---|
| EX-01 | 涂下排机柜区：“优化现有机柜符号的线条，不增减设备，不移动墙、门和房名” | appearance；局部模型比较 | 原结构保护区不变；原有设备数量经人工复核；IMAGE_ONLY 不升级 CURRENT |
| EX-02 | 同一区域：“改成两排、每排三个机柜，上侧留通道” | layout / equipment_layout；对象化六个符号，再可选局部表现 | 数量由六个对象保证，不靠模型猜；无尺寸时只叫示意，不承诺检修净距 |
| EX-03 | 在办公室文字上选择：“房名改为运行办公室，不改家具” | 语义/标注补丁＋程序排字，通常不调用生图 | 中文准确；房间语义同步；只写回已批准文字区域 |
| EX-04 | 选择机房与机柜区之间墙：“打通两个房间” | layout；先提出墙/门/房间拓扑补丁并请求确认 | 首期只做到风险提示/阻断；后续有几何时才进入结构修改验收 |

演示“移动楼梯 A”时必须触发跨层影响审批。对只有一层图片的会话，应提示缺少其他楼层和几何，不能自动生成“全楼已同步”的结果。

## 05｜产品交互详细设计

### 5.1 页面布局

```text
顶部：项目 / 建筑 / 楼层 / 当前版本 / IMAGE_ONLY 或 CURRENT / 本机后端状态
左栏：画笔  橡皮  矩形  多边形  保护笔  撤销  重做  重置视图
中间：原图画布 + 编辑色层 + 保护色层 + 上下文虚线框 + 坐标提示
右栏：修改描述 / 修改类别 / 解析后的操作摘要 / 冲突提示 / 生成按钮
底部：候选条 / 原图-结果滑杆 / 并排 / 差异 / 接受 / 拒绝 / 历史时间线
```

默认显示与任务有关的少量设置：笔刷大小、修改强度、保持墙门、保持房名、一次候选数。模型文件、采样器、种子、上下文 padding、蒙版 grow/feather、精度模式放入高级面板；默认一次一个候选，多个候选串行而非同时占内存。

### 5.2 标准交互流程

| 步骤 | 用户看到什么 | 系统必须完成什么 |
|---|---|---|
| 导入 | 原图、分辨率、来源版本、尺度状态 | 保存原字节；按 EXIF/颜色约定生成会话规范图；计算两个哈希 |
| 涂抹 | 实时半透明选区，可擦除或撤销 | 记录原图坐标笔画，不把鼠标每移动一次都建业务版本 |
| 输入描述 | 原话＋模型/规则解析的简短摘要 | 保留原话，判断是否涉及对象数量、用途、实体边界或跨层设施 |
| 预览权限 | 绿：可改；橙：保护；蓝框：只读上下文 | 显示实际 A、P、C；冻结参数、base revision 和权限哈希 |
| 生成 | 排队/加载/推理/校验的真实状态 | 先持久化请求再执行；不能靠假百分比表现进度 |
| 比较 | 原始模型候选与最终合成版可切换 | 保留两者；显示区外检查、几何状态和剩余问题 |
| 接受 | 新版本编号与用途影响 | 事务比较 head，创建新修订与审批事件，不覆盖旧图 |
| 拒绝 | 候选留在历史中，当前版本不变 | 保存拒绝原因；新的尝试使用新 attempt_id |
| 回滚 | 选择恢复到哪个历史内容 | 创建恢复修订，记录恢复来源，不删除期间的版本 |

### 5.3 画笔行为规范

笔刷默认按“原图像素”计半径，缩放时屏幕视觉宽度随倍率变化，UI 明示单位。需要“屏幕固定宽度”模式时，保存转换后的原图半径，不能只存 CSS 数字。支持方括号调笔宽、空格拖动画布、滚轮围绕鼠标缩放、Esc 结束工具。快捷键不得在用户输入提示词时抢走按键。

橡皮仅擦除蒙版层，不擦原图。画笔撤销属于未提交草稿；版本回滚属于业务历史，两者独立。离开页面前提示未保存选区，草稿可保存到 IndexedDB，但已提交任务和业务历史以后端为准。

鼠标越界、失焦、切标签、pointercancel 或松开时都必须结束本次 stroke，防止出现贯穿整图的意外线条。使用 pointer capture；首期可禁用绘画过程中缩放/旋转，以降低坐标歧义。

### 5.4 提示词与风险提醒

“涂到墙上”不等于授权改墙；“保持不变”也不是系统已完成保护。冲突预览明确列出：碰到墙/门/文字的区域、被保护规则裁掉多少、是否可能删除设备、是否需要新增房间功能参数。

名称相同的多个机柜区，以用户选区位置为目标，不按文字随机选一个。“把这个改成机房”若只圈房名，需要询问是改标签还是改用途/设备；先展示拟执行范围，不直接开始。

单次操作可以含多笔不连通选区，但首期按一个逻辑区域处理；相距很远或目的不同，建议拆分。系统不得为了便于生成而静默用大矩形把中间未选中的房间一并授权。

## 06｜蒙版、坐标与权限：最容易出错的部分

### 6.1 至少分开六个概念

| 符号 | 名称 | 语义 |
|---|---|---|
| E | 用户原始涂抹 | 原笔画栅格化结果；不可覆盖，作为证据 |
| P | 保护区 | 墙、门、核心、文字、用户锁定物件的已确认区域 |
| A | 批准的有效修改区 | E 经规则裁剪、用户确认后的硬权限；白=允许修改 |
| C | 上下文裁切范围 | 模型需要看的周围内容；可以比 A 大，但没有额外写权限 |
| M | 模型噪声/重绘蒙版 | 传给后端的采样控制，可能包含经登记的辅助扩张 |
| B | 最终混合 alpha | 决定哪些生成像素能写回；范围必须严格包含于 A |

常规情况下 `A = E ∩ floor_area − P`。IMAGE_ONLY 没有可信 floor_area/P 时，用户人工确认；启发式识别只产出保护建议，不能标为精确建筑实体。

A 的扩张必须重新预览并获准。C 的扩张只改变模型上下文。M 若为了接缝而扩张到 A 外，其输出只存在于 raw，不得由此扩大 B。首期建议 M 也约束在 A 内，减少原始模型泄漏。

权限硬蒙版使用 8-bit 单通道 PNG，只允许 0/255。B 可以有灰度；不能把“蒙版预览 30% 透明度”误当成“模型只改 30%”。B 默认使用向内羽化，不能将羽化影响扩到 A 之外。

### 6.2 最终像素保护公式

令 I 为规范化原图，G 为完成逆裁切和尺寸还原的模型候选。在授权区域内部按 B 混合，外部直接复制 I：

```text
B(p) = 0                      当 A(p) = 0 或 P(p) = 1
F(p) = round(B(p)G(p) + (1-B(p))I(p))  仅在 A 内计算
F[非 A] = I[非 A]             整数像素直接复制，作为最后一道操作
F[P] = I[P]
```

文字、矢量符号、墙门补丁也必须遵守同一个授权写入区。否则“模型在区外没改动，但程序重新标注时改了区外”仍然是不合格。合法的文字或墙更新范围要事先并入批准 A，并留审批证据。

按最终无损 PNG 的**解码后规范 RGBA/RGB 像素数组**检验：`changed_pixels_outside_A = 0`。文件压缩字节、PNG 元数据不同不代表像素不同；指标不应比较整文件是否完全相同。

Diffusers 官方文档指出，即使是 inpaint 模型也可能改变未遮罩区域，并提供 overlay 强制保留的做法。P2 的严格回贴是系统控制，不是把它包装成模型能力。[S12]

### 6.3 坐标链

保存四个坐标层：浏览器 CSS 视口 → 原图像素 → 模型工作图 → 建筑世界坐标（已知时）。`devicePixelRatio` 仅用于画布 backing store，不应在事件坐标中反复乘。

```text
image_to_canvas = viewport_fit × pan_zoom
image_point = inverse(image_to_canvas) × canvas_css_point
model_point = image_to_model × image_point
world_point = pixel_to_world × image_point   # 仅尺度已经确认时使用
```

事件先减去画布在页面中的位置，再做逆矩阵；`getPointerPosition()` 不是已自动转换的原图坐标。Konva 官方专门说明了嵌套缩放/平移时要使用逆绝对变换。[S09]

矩形范围统一为半开区间 `[x0,y0,x1,y1)`；像素采样采用中心 `(u+0.5,v+0.5)`。裁切、等比缩放、padding 的顺序和插值算法必须入记录，防止回贴漂移一个像素。图与 mask 同步变换：硬权限最近邻，软 alpha 单独处理；禁止把图和 mask 各自按不同的长宽拉伸。

### 6.4 需要进入测试的错误

50% 与 200% 缩放画同一位置；Retina DPR=2；页面滚动后涂抹；侧栏展开后画布移动；图片 contain 留白；窄选区；贴边选区；选区内保护孔洞；全黑/全白/反向 mask；多笔撤销；浏览器色彩空间与透明通道。空 A 返回 EMPTY_MASK，不调用模型。

## 07｜后端区域重绘算法与工作流

### 7.1 固定处理流程

```text
规范图＋输入版本＋笔画＋文字
  → 校验版本、图像哈希、蒙版尺寸
  → 解析修改意图，生成简短公开操作计划
  → 保护区与权限预览，冻结批准 A
  → 计算 C 和模型工作图变换
  → 去除/保护文字，选择控制图与模型分支
  → 本机模型生成 raw crop
  → 按既定矩阵回投，不做全图自由变形对齐
  → 合成授权区域，叠加获准标注/符号
  → 区外像素、区域语义、几何与版本校验
  → 暂存候选，等待接受或拒绝
```

### 7.2 裁切策略

C 取 A 的包围盒加上下文，而不是把整张图缩小到 512。图片示例的 C 为 188×216 像素；可等比放大并 padding 到模型工作尺寸，推理后严格逆变换回原图。

上下文默认可以从原图长边的 5% 起步，限制在 32—128 像素，并让用户预览调整；这是待测试参数，不是模型最佳值。窄区域需纳入足够相邻墙和门的上下文；小于几十像素的目标不必盲目上大模型，考虑矢量重绘。

先裁后缩，保持纵横比；SD 系列通常按后端要求填充到合法尺寸，具体倍数记录在 adapter capability 中，而不是对所有模型硬编码同一个值。有效 mask 必须离最终 padding 边界有定义，回贴时去掉 padding。

### 7.3 两条 ComfyUI 起步分支

**A. SD1.5 基础 checkpoint，作为已有资源可复用基线：**

```text
LoadImage(裁切图) → VAEEncode → SetLatentNoiseMask(M)
CLIPTextEncode(正/负提示) → 可选 ControlNetApplyAdvanced
以上进入 KSampler → VAEDecode → 保存 raw → P2 回贴校验
```

**B. 专用 SD1.5 Inpainting checkpoint，作为质量候选：**

```text
LoadImage(裁切图) + 独立蒙版 + CLIP 正/负条件 + VAE
  → InpaintModelConditioning
  → 可选兼容的 ControlNet 条件
  → KSampler → VAEDecode → 保存 raw → P2 回贴校验
```

专用 inpaint 条件与基础 checkpoint 不是随意交换的节点。`InpaintModelConditioning` 源码同时生成 conditioning 和 latent，`noise_mask` 的效果也依赖模型；`VAEEncodeForInpaint` 则会预处理遮罩内像素并有 grow 行为。部署时固定节点版本，分别验证分支，不复制一个节点名就认定等价。[S07]

为了消除 alpha 歧义，P2 默认上传独立灰度蒙版，再明确通过 `ImageToMask` 的灰度通道转为 MASK。ComfyUI 的 LoadImage mask 路径还涉及 alpha 反转；不能把不透明灰度 PNG 的 MASK 输出误认为其亮度。加入黑白角标测试确认“白=修改”。[S07][S15]

### 7.4 不让旧 Canny 把要删除的东西锁死

用户要删除机柜时，直接对原图做 Canny 会把机柜轮廓也变成控制条件，导致模型不断画回原机柜。这是本项目需要避免的条件冲突。

有几何时：控制图只绘制保持的墙、门、核心和已经确认的目标对象；不保留被删除对象的旧边缘。没有几何时：先在修改区清理旧对象边缘，保护边缘由人工确认，必要时降低或关闭 Canny，记录实际策略。

移动墙时控制图必须来自目标几何补丁，不能继续使用旧墙 Canny。也不能在模型出图后重叠旧墙线来掩盖不一致。

### 7.5 改动强度不是统一魔法数

“保留外观细修”可从低重绘强度开始；“替换对象”通常需要更充分改变。示例搜索区间：外观细修 0.25—0.45，对象替换 0.55—0.85，步数 20—28。只作为 SD 系列试验起点；不同初始化、专用 inpaint 模型和采样器需要单独试验，不承诺某个数值普遍最优。

Differential Diffusion 可作为灰度重绘强度控制的后续实验项，但不是权限边界；最终权限仍由 A 和合成规则保证。[S16]

### 7.6 中文、数量和线稿为何分开做

普通平面图有大量中文标签和重复矩形设备。模型负责局部表现；中文用本机字体排版；准确数量与排列优先建立参数化对象。

例如两排三个机柜：先有六个 cabinet IDs 和二维框。默认由程序渲染并保护这六个符号，模型只改其他获准的表现区域；若放开设备符号参与生成，仍必须逐一核对图面数量，失败就拒绝候选，不能因 JSON 写着六个便宣称图中一定有六个。没有真实尺度只存像素示意与 `measurement_status=UNKNOWN`；不能编造每个机柜长宽或通道符合标准。

扁平图片中旧中文已烘焙进去时，直接在上面加字会重影。必须单独批准旧文字区域清理；无法恢复被字遮住的背景时保留不确定性，不叫无损恢复。为后续效率，建议 P1 输出无字图、文字层、墙门层和对象侧车，但 P2 不能以此为前提拒绝一切外部图片。

## 08｜Mac mini 16GB 的模型分层与选择

### 8.1 候选而非实测排名

本轮不安装模型、不运行性能测试；下表均登记为 **NOT_RUN**。16GB 是统一内存预算，不等同于 16GB 独立显存。起步一次一图、一个推理 worker；模型和可选 VLM 不同时驻留。

| 层级/角色 | 候选 | 适用任务与主要限制 | 推荐动作 |
|---|---|---|---|
| T0 确定性基线 | 背景清理、程序中文、参数化矩形/设备符号 | 数量、标注、保持几何；不是生成模型 | 必做基线，比较模型是否有额外价值 |
| T1 遮罩生成基线 | 已有 SD1.5 + masked img2img，可选兼容 Canny | 复用 P1 权重，但必须新接 mask，不是旧整图工作流 | 首先验证接口和安全回贴 |
| T1 专用重绘 | `stable-diffusion-v1-5/stable-diffusion-inpainting` | 图＋mask＋文字，512 级起步；分发仓库是原模型的镜像维护入口 | 与上一项同案例比较，不预设必胜。[S13] |
| T1 消除专用 | LaMa | 移除符号并补背景，不按文字生成六个机柜 | 只纳入“消除”赛道，保持独立兼容性验证。[S17] |
| T2 更高质量候选 | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` | 更大的专用重绘模型；局部工作图从 768 级试起，不起步就叠 Refiner | 完整管线实测内存与接受率。[S14] |
| T2 指令编辑候选 | FLUX.2 klein 4B 兼容量化方案 | 支持参考图编辑；普通编辑接口不等于原生硬蒙版，应走 crop-edit-composite adapter | 先验证运行后端和接口；保持原图区外的责任在 P2。[S18] |
| 可选意图/视觉助手 | Qwen2.5-VL-3B-Instruct 的受支持本地版本 | 提议选区对象、指令拆解；不是像素编辑器，也不是几何事实来源 | 首期不是必需，使用后卸载再生图。[S19] |
| T3 专项研究 | BrushNet、PowerPaint 等 | 面向重绘的专门方法；增加模型/节点依赖 | 先验证后端/MPS，不能因为 SD 基础就假定可在 Mac 无修改运行。[S20][S21] |

FLUX.2 klein 4B 的官方消费级 GPU 内存口径不能直接当作 Mac mini 16GB 的完整应用预算，量化格式也必须由选定后端真实支持。最终推荐以用户机器实测为准，不引用官方 GPU 秒数冒充本机速度。[S18]

### 8.2 推荐实施顺序

先做 **SD1.5 遮罩分支 + 专用 inpaint 对比**；通过后测试 SDXL；FLUX.2 klein 4B 留作独立指令编辑比较。LaMa 只参加消除任务。精确文字/数量任务始终保留 T0 路线。

前端不直接面对模型文件名，使用 `backend_profile_id`。后台能力表声明：支持任务、是否原生 mask、允许的分辨率、精度/量化、是否支持 ControlNet、是否返回 raw、能否安全取消。未支持的功能应灰显或拒绝，而非静默降级。

### 8.3 本机资源治理

推理前检查模型可见、后端 `/object_info` 节点存在、空闲空间与目标尺寸。模型文件可见或加载成功都不等于执行完成；必须真正完成推理、收到并校验原始输出后，才登记 `MODEL_EXECUTED`。记录 Apple 芯片、系统、内存、Python/PyTorch/MPS或其他后端、权重 SHA、自定义节点版本。

OOM 后只提供有记录的降分辨率/裁小上下文/更换已批准模型选项；创建新 attempt，不偷偷改变原实验配置。禁止自动启动云推理、关闭系统内存保护或污染用户其他 Conda 环境。首次权重下载与常态推理联网分开授权。

## 09｜与几何和 P3 的一致性

### 9.1 两种入口

| 输入 | 允许的 P2 行为 | P3 交接 |
|---|---|---|
| P1 PlanRevision + CURRENT 几何 + 已知尺度 | 可按对象保护、语义编辑、补丁校验 | 新版本的图片、几何、尺度和审批匹配后才可交接 |
| 外部 PNG/JPG，无几何/尺度 | 可做受限图面编辑，保护区人工确认；新增语义仅为候选 | 保持 IMAGE_ONLY；先校准和重建，不能直接交付米制成果 |

不能因为用户点“接受图片”就从 IMAGE_ONLY 跳到 CURRENT，也不能只看“墙似乎没变”就认定模型没有制造假墙。

### 9.2 修改分类按实际影响判定

`appearance` 只用于同对象、同数量、同功能、同几何的表现调整。`layout` 覆盖对象增删/移动、房间功能变化、门墙变化和跨层核心变化；可用 `intent.subtype` 区分，不擅自扩充当前合同顶层枚举。

中文房名改为“运行办公室”可能是纯显示更正，也可能是房间用途变化。前者更新标注层；后者同步 room function 元数据。若目前的 geometry sidecar 不包含设备或用途，新增独立语义侧车并评审合同，而不是把变化丢掉。

### 9.3 几何补丁与审批

补丁绑定 base geometry hash，使用允许的类型化操作，如 `update_room_function`、`add_equipment`、`move_door`、`replace_partition`。不执行模型写出的任意 Python、SQL 或可执行表达式。应用前检查引用对象存在、操作区域获准、房间包含/重叠、门连接、跨层 core IDs。

改变楼梯、管井、外壳的请求先出影响集合：涉及楼层和核心对象、可能失效的尺寸/成果、所需资料。审批绑定具体 base、A、补丁和版本；任何变化重新批准。

### 9.4 状态推进规则

```text
IMAGE_ONLY → 取得几何与尺度证据并审核 → CURRENT
CURRENT + 未同步布局修改 → STALE
STALE + 对应版本几何重建和核验 → CURRENT
CURRENT + 图面调整 → 几何复核通过后仍 CURRENT，否则 STALE
```

即便 CURRENT，也要结合 approval_event_id 和 P3 专业输入要求，不能视为施工批准。P3 交付继续遵守仅 DXF / PDF / GLB；P2 的内部 JSON、mask、日志不自动变成额外建筑交付。

## 10｜修改前、修改后、过程如何长期记录

### 10.1 四个对象，不混用

**Draft** 是未提交的画笔/提示词草稿。**EditRequest** 是冻结后的业务意图与权限。**Attempt/Candidate** 是某一模型和种子的一次执行及结果。**Revision** 是被接受或恢复的新版本。

一次 request 可以有多次 attempt，但不因用户刷新页面生成新 request；同一候选可拒绝，其他候选继续评估。候选不是当前版本，接受前不得改变当前 head。

### 10.2 不可变文件与追加事件

SQLite 保存 sessions、revisions、edit_requests、attempts、artifacts、events、approvals、outbox、leases。原图、蒙版、工作图、原始结果、最终图和差异图按内容 SHA 存储，引用关系去重；不为每个 before 重复保存一份相同大图。

文件先写临时目录、校验哈希并原子改名到对象目录，随后在数据库事务中提交引用。数据库与文件系统不是天然同一事务，崩溃可能留下孤立对象；后台只在确认无引用且满足保留策略后清理，不能直接删正在使用的文件。

一次请求至少保存：

| 范畴 | 数据 |
|---|---|
| 来源 | original_file、canonical_image、before revision、floor、尺寸、图像/几何 hash |
| 交互 | strokes、笔刷单位、工具、时间、原图坐标、视图矩阵、E/P/A/C/M/B |
| 指令 | 用户原话、结构化意图、公开操作摘要、模型正/负提示、模板版本 |
| 运行 | 权重/量化/后端/节点版本、seed、steps、cfg、denoise、控制参数、workflow、裁切矩阵 |
| 结果 | raw crop、还原 raw、final、差异、指标、几何/语义补丁、错误及警告 |
| 决策 | 接受/拒绝原因、操作者、审批版本、parent、restore_from、下游失效事件 |

“过程”是这些可见输入、步骤和结果，不存储或索取模型隐藏思维链。事件序列及内容哈希可用于完整性检查，不等于防有权限的管理员篡改；访问控制、备份、保留和删除授权另行管理。

### 10.3 状态机

```text
DRAFT → PREVIEWED → APPROVED_FOR_EXECUTION → QUEUED
      → PREPARING → SUBMITTING → RUNNING → VALIDATING → CANDIDATE_READY
      → ACCEPTED / REJECTED

可能的旁路：NEEDS_CONFIRMATION / BLOCKED / FAILED / CANCELLED /
           CONFLICT / SUBMISSION_UNKNOWN
```

执行状态、用户接受状态、几何状态是不同维度。`SUCCEEDED` 只表示生成链路完成，不表示用户接受；`ACCEPTED` 也不覆盖 `geometry_status=STALE`。

### 10.4 幂等与并发

`idempotency_key` 在用户/会话范围唯一，绑定规范请求哈希。相同 key 和相同输入返回已有 request；相同 key 不同输入返回 409。不同参数、模型或 seed 创建新的 attempt，不篡改旧运行记录。

接受候选时，在同一事务中比较 `expected_head_revision_id`；若另一标签页已更新 head，返回 CONFLICT，候选保留为分叉。MVP 不自动合并两张图，避免把语义冲突掩盖成像素拼接。

恢复旧内容生成新 revision，例如 `r0 → r1 → r2 → r3`，r3 的 `restore_from=r0`、parent=r2。这样既能恢复旧图，也保留中间发生过什么。

### 10.5 崩溃、重复提交与取消

请求和 outbox 先持久化，再领取带 lease 的任务。worker 重启按 lease 和外部 prompt ID 恢复，不能无条件重新提交。

**ComfyUI 接口不能直接视为业务级 exactly-once 服务。** 若它接受了 `/prompt`，而 P2 在保存 prompt ID 前崩溃，会有提交结果未知窗口。记录 `SUBMISSION_UNKNOWN`，尽量通过带 request 标记的 workflow/队列/历史核对；无法确认则由用户选择继续等待或显式重试，不自动重复生成。[S06]

排队中任务可精确取消本任务 ID。运行中请求的取消必须确认后端支持按任务取消；共用 ComfyUI 时不要调用全局 interrupt 打断其他应用。MVP 可将本请求标为取消并丢弃迟到结果，但 UI 必须说明底层计算可能仍在进行。独占实例才允许经所有权核对后中断。

## 11｜API 与数据对象设计

### 11.1 接口表（提案，不是当前已存在的接口）

| 方法与路径 | 用途 | 关键行为 |
|---|---|---|
| `POST /v1/p2/sessions/import` | 上传图片或已有 PlanRevision 引用 | IMAGE_ONLY 路径不伪造尺度；返回规范尺寸和会话 ID |
| `POST /v1/p2/edit-plans/preview` | 根据笔画、保护与描述生成计划 | 返回 A/C/P、冲突、意图与计划哈希，不生成 |
| `POST /v1/p2/jobs` | 提交批准的计划 | 幂等检查、base/head 检查、先持久化，202 返回 job ID |
| `GET /v1/p2/jobs/{id}` | 状态与候选 | 返回真实阶段、错误、后端 prompt ID（权限允许时） |
| `GET /v1/p2/jobs/{id}/events` | SSE 状态事件 | 支持 Last-Event-ID；断线重连不重新提交 |
| `POST /v1/p2/jobs/{id}/cancel` | 取消请求 | 按后端能力声明执行，不中断无关任务 |
| `POST /v1/p2/candidates/{id}/accept` | 接受候选 | expected_head CAS；创建 revision 和接受事件 |
| `POST /v1/p2/candidates/{id}/reject` | 拒绝候选 | 保存原因，不改变 head |
| `POST /v1/p2/revisions/{id}/restore` | 恢复历史内容 | 新建恢复修订，保留来源 |
| `GET /v1/p2/revisions/{id}/audit` | 查看公开修改过程 | 不包含凭据、隐藏思维链或任意服务器文件 |

上传文件不接收任意服务端绝对路径。资源以受控 artifact ID 读取；限制文件类型、像素数和压缩炸弹，规范化 EXIF 旋转。原图不可因浏览器缩略图被替换成低分辨率版本。

### 11.2 错误码

`EMPTY_MASK`、`MASK_SIZE_MISMATCH`、`INVALID_TRANSFORM`、`PROTECTED_REGION_CONFLICT`、`AMBIGUOUS_INSTRUCTION`、`UNCONFIRMED_CROSS_FLOOR_CHANGE`、`STALE_BASE_REVISION`、`GEOMETRY_REQUIRED`、`MODEL_UNAVAILABLE`、`INCOMPATIBLE_PIPELINE`、`OUT_OF_MEMORY`、`OUTPUT_SHAPE_MISMATCH`、`UNAUTHORIZED_PIXEL_CHANGE`、`SUBMISSION_UNKNOWN`、`P3_BLOCKED_STALE_GEOMETRY`。

返回结构含错误码、可读说明、request/attempt ID、是否可重试和修复建议。失败日志是正式产物；不要吞掉异常后返回“生成完成”。

### 11.3 ImageEditSession 最小字段

`session_id`、可选 project/building/floor、original artifact、canonical artifact、image_size、color/alpha profile、geometry_ref（可空）、geometry_status、scale_status、pixel_to_world（未知为 null）、current_revision_id、created_at。未确认楼层用会话临时标识，不冒充用户提供的 1F。

### 11.4 执行计划至少固定这些哈希

base canonical pixels、base geometry、E/P/A/C/M/B、request canonical JSON、actual prompt、workflow、model weights、adapter version。为了审计稳定，JSON 采用约定排序与编码，不把临时绝对路径、UI 当前缩放或无关时间混入重复请求判断。

人工审批绑定计划哈希；用户改了 mask、提示词、模型能力或影响范围后，应重新预览。纯 seed 换候选是否重新批准由策略明确：同权限/同目标可沿用执行授权，但必须新建 attempt。

## 12｜实现目录与复用边界

建议 P2 保持独立安装，不跨 import P1 的 baseline 私有脚本：

```text
projects/region-edit/
  pyproject.toml
  README.md
  frontend/
    src/editor/       # Stage、Stroke、MaskPreview、Compare、History
    src/api/          # 与本机业务API通讯
    tests/            # Playwright 坐标与交互
  src/autoplan_region/
    api/              # sessions、preview、jobs、revisions
    domain/           # request、attempt、revision、policies
    masks/            # 原图栅格化、权限、保护、羽化
    imaging/          # 规范化、裁切、回贴、差异
    geometry/         # 类型化补丁、影响集合、失效
    persistence/      # SQLite、CAS、事件、outbox
    workers/          # lease、恢复、串行队列
    adapters/         # comfy_sd15、comfy_sdxl、crop_edit
    evaluation/       # 技术指标、人工评分、实验登记
  workflows/          # 固定版本模板与节点说明
  tests/              # 单元、合同、故障注入
```

共用合同和模型运行协议放仓库明确的 shared/contracts 边界，经治理任务批准；不是直接把三项目源码互相引用。P1 旧客户端中 localhost 校验、失败留痕等可经过测试提取，但需要新写 masked workflow 和任务生命周期。

前端→P2 API 使用本机会话 token 和严格 Origin 检查；P2→ComfyUI 不让浏览器直接暴露所有工作流能力。即使监听 localhost，也应防恶意网页跨站请求。默认关闭遥测、云模型、第三方提示词翻译；日志与用户图片不进入公共 Git。

## 13｜模型比较、系统测试与验收指标

### 13.1 不用一个总分掩盖失败

分开评价：权限与系统正确性、模型任务质量、几何/语义同步、用户交互、资源代价。区外最终改动或错误版本接受等硬失败不能被“画得好看”抵消。

| 指标 | 测量对象 | 目标或判据 |
|---|---|---|
| Final outside-A changes | 原图与最终规范 PNG | 必须 0 像素；保护区同样为 0 |
| Raw leakage | 模型实际处理的上下文中非 M 区域 | 单独报告；不能以合成后为 0 代替 |
| ROI registration | 裁切/缩放/回贴 | 合成回贴单像素测试通过；错误尺寸直接拒绝 |
| Instruction completion | 被要求修改的对象/样式/用途 | 逐案例人工 PASS/FAIL＋原因；必要时统计分级 |
| Exact object count | 参数化设备任务 | 对象数据必须等于目标数量，图面逐一可核对 |
| Wall/door/core invariance | 几何与对应保护图 | 不获准不变；缺少可信几何时标记未验证 |
| History completeness | 每次请求、失败、接受、拒绝、恢复 | 必填证据完整；源文件哈希可验证 |
| P3 invalidation | 接受后的修订状态 | STALE / IMAGE_ONLY 不可偷偷放行 |
| Resources | 真实 Mac 冷/热启动各阶段 | 记录耗时、RSS、后端显存/MPS分配、系统压力，分别注明口径 |

RAW 在模型分辨率下与“同样预处理的 before”比较，避免把缩放插值本身算作模型泄漏；再单独报告回投到原图的变化。若 raw 未覆盖全图，只评测该上下文，不能把未处理区域填零后声称模型整图无泄漏。若无非 M 区域，标 N/A，不做零分伪结论。

### 13.2 公平实验设计

首轮开发集采用 8 个经确认的编辑任务，每个支持该任务的图像编辑候选各跑 3 个固定种子，所有尝试留痕。例如 3 个可比候选×8 任务×3 种子=72 次尝试，这是待执行预算，不是已完成结果。

固定输入版本、授权 A、保护 P、任务目标和候选次数；允许各模型使用已登记的原生尺寸/提示模板，但分别记录，避免强迫不同架构用不兼容参数。相同数值 seed 不代表跨模型相同噪声；它只帮助各自复现。

LaMa 单列消除赛道，VLM 单列意图/识别赛道，T0 单列确定性路线。不要把不支持文字生成的模型算成对象替换失败，也不要用更大硬件的时间与 Mac 混榜。保留不同图纸/任务的留出集，不能只在这一张图上调好就称为泛化。

### 13.3 建议的首期回归集合

画布：25%、50%、100%、200% 缩放，DPR 1/2，滚动/留白/拖动、快速划线、离开画布、撤销擦除、保护孔洞。

图像：PNG/JPG 导入、RGBA、EXIF 旋转、黑白反转、无 alpha 的 mask、空区、小区、边缘区、全图区、两个不连通区、非整除模型尺寸。

持久化：同幂等键重复点击、同键不同 body、两个标签页同时接受、提交后断网、收到 prompt ID 前崩溃、模型结束前取消、磁盘满、文件写入后数据库回滚、事件重连。

业务：错误 floor、来源图替换、geometry hash 不符、未批准移动核心、IMAGE_ONLY 请求米制移门、只改房名、对象数增减、STALE 交接 P3、三轮编辑中拒绝一次并恢复一次。

### 13.4 MVP 的发布条件

至少一个本机真实模型完成指定区域任务；完整通过：三轮编辑、一次拒绝、一次恢复、一次并发冲突、一次故障恢复；最终授权区外差为 0；每个候选 raw/final 都存在；不把 mock/dry-run 当模型验证；用户确认一栋图的可用性。性能目标在设备基线建立后再冻结，不事先承诺秒级。

## 14｜映射到现有开发台账

不重命名或覆盖原 `P2-01`—`P2-05`。以下为建议子任务和验收证据，尚未修改仓库台账。[R04]

| 任务 | 建议子任务 | 交付证据 | 依赖 |
|---|---|---|---|
| P2-01 | 导入规范化；画布笔刷/擦除；原图坐标；保护区；权限预览 | 截图、导出 mask、Playwright 坐标测试、笔画回放 | 当前 READY；可先做 IMAGE_ONLY 会话 |
| P2-02 | ImageEditSession；不可变对象；追加事件；CAS；幂等；恢复 | SQLite 测试、失败/冲突记录、完整 revision 谱系 | GOV-01 合同评审；不得先做无历史的“临时生成接口” |
| P2-03 | SD1.5 masked workflow；专用 inpaint 分支；裁切回贴；raw/final | 本机三轮结果、运行参数、区外差值测试 | P2-01、P2-02 |
| P2-04 | 几何/语义补丁；核心影响；批准绑定；P3 失效 | STALE 阻断与跨层审批正反用例 | P2-03、GOV-02 |
| P2-05 | 可比模型登记；留出集；三轮验收与恢复 | 全部尝试记录、分赛道比较报告、用户接受原因 | P2-04、BENCH-02 |

推荐先完成 P2-01 与 P2-02 的最小闭环，再接一个模型；不是先开多个模型、等 UI 做完再补日志。P2 不必等 P1 选型结束，但完整跨项目交接仍受合同和几何任务约束。

### 14.1 里程碑交付物

**D0 设计冻结：** 本设计、ADR、未知尺度会话合同、样例授权声明。  
**D1 无模型可用编辑器：** 上传、涂抹、保护、比较、程序可控候选、接受/拒绝/恢复。  
**D2 单模型闭环：** 专用本机工作流、真实 raw/final、失败恢复和监控。  
**D3 结构联动：** 对象/标签/房间补丁，跨层门禁和 P3 状态。  
**D4 对比验收：** SD1.5、SDXL或其他受支持候选的同任务实测，不预设赢家。

这里按验收阶段排程，不在未知开发人手和模型运行情况时承诺日历日期。

## 15｜关键风险与架构决策

| 风险 | 后果 | 对策 |
|---|---|---|
| 旧图当新版本 | 在错误平面上修改 | base/head/hash 三重绑定与 CAS |
| 区域坐标漂移 | 改到邻房或墙 | 原图笔画、逆矩阵、半开区间、回贴回归 |
| grow/blur 暗扩区 | 用户未涂区域被改 | A 独立冻结；只向内羽化；最后原像素拷回 |
| 旧 Canny 锁对象 | 删除后又画回来 | 条件图去掉待删对象，保留确认的结构 |
| 新假墙/假门 | 图像看似完整但几何错误 | raw 审查、受保护结构图及 CURRENT/STALE 分开 |
| 中文糊掉、数量不准 | 无法用于后续设计 | 程序标签与对象化精确数量 |
| 小图被放大成伪精度 | P3 尺寸错误 | 只叫像素示意，尺度未知保持未知 |
| 框架或插件维护变化 | 安装失败或漏洞 | 固定版本、最小依赖、供应链清单；归档项目不作为主干 |
| 提交结果未知时自动重试 | 重复占用算力，版本混乱 | SUBMISSION_UNKNOWN 与 prompt/workflow 核对 |
| 审批与实体版本脱节 | 旧批准给新几何放行 | 批准绑定具体计划与影响对象哈希 |

建议新增 ADR：ADR-P2-001 自建 WebUI＋本机 ComfyUI；002 六类蒙版；003 未知尺度会话；004 不可变历史＋CAS；005 精确对象走几何，生图只做表现。ADR 状态均为 PROPOSED，待负责人评审，不当作已批准规范。

## 16｜用这张图进行首轮现场验收

验收前在本机保存原图，核对 768×512 和来源哈希；不先缩小、不替换成先前 H 形图、不带入不属于它的尺寸。

第一轮做 EX-01：只调整下排机柜符号，生成后分别看 raw 和 final；A 外逐像素必须为零变化。接受为 r1，原图 r0 保留。

第二轮做 EX-03：修改办公室房名。显示拟改变文字及语义范围，使用程序标注；用户故意拒绝候选，head 仍为 r1，拒绝原因和候选仍在历史。

第三轮做 EX-02：提出两排三个机柜。先生成六个对象草图，用户确认示意范围；真实尺度仍未知。可接受图面为 r2，但 IMAGE_ONLY 不得自动交给 P3。

随后恢复 r0 内容，生成 r3；并从另一个标签页尝试接受基于 r1 的旧候选，必须返回 CONFLICT。再执行一次 worker 重启或后端断线，检查恢复记录而不是重复生成。

最后输出私有验收包：r0/r1/r2/r3 谱系、失败/拒绝候选、原话/实际提示、蒙版、raw/final、差异图、参数/版本/耗时及未解决项。把“用户说图片满意”和“结构/尺寸可交付”分别记录。

## 17｜示例请求与提示词

### 17.1 IMAGE_ONLY 会话示例（内部对象，不冒充现有 0.1.0 PlanRevision）

```json
{
  "design_schema": "p2.image-session.proposed-1",
  "session_id": "example-session",
  "image_size": [768, 512],
  "geometry_status": "IMAGE_ONLY",
  "geometry_ref": null,
  "scale_status": "UNKNOWN",
  "pixel_to_world": null,
  "current_revision_id": "example-r0",
  "capabilities": {
    "pixel_edit": true,
    "measured_layout_edit": false,
    "p3_handoff": false
  }
}
```

### 17.2 冻结后的执行计划片段

```json
{
  "design_schema": "p2.edit-plan.proposed-1",
  "session_id": "example-session",
  "base_revision_id": "example-r0",
  "expected_head_revision_id": "example-r0",
  "edit_type": "appearance",
  "instruction": "优化现有机柜符号线条，不增减设备，不改墙门和房名",
  "mask_white_means": "EDITABLE",
  "source_image_size": [768, 512],
  "context_bbox_xyxy": [210, 280, 398, 496],
  "mask_artifact_id": "example-authorized-mask",
  "protected_label_bbox_xyxy": [267, 407, 340, 434],
  "backend_profile_id": "sd15-inpaint-local-candidate",
  "candidate_count": 1,
  "execution_status": "NOT_RUN",
  "scope_approval_status": "PENDING"
}
```

上面是字段说明，不是可绕过哈希/审批直接运行的正式请求；生产接口必须填入真实 artifact 引用、执行计划哈希和幂等键。文档附带的 JSON 也标为 DESIGN_FIXTURE_ONLY。

### 17.3 模型提示词编译

保留中文用户原话，并将结构与表现目标编译为模型所需文本。首期可使用本机固定模板，无须为翻译调用云模型。

正向示例：

```text
Orthographic top-down architectural floor plan. Refine the existing
cabinet symbols inside the selected room, keeping their count and
positions. Flat pale blue room fill, thin dark technical lines.
Preserve the approved wall and doorway layout. No perspective.
```

负向示例：

```text
photorealistic, perspective, isometric, 3d facade, people,
extra walls, blocked doorways, merged rooms, new staircases,
text, letters, dimensions, scale bar, watermark
```

这些文字只表达意图，不是硬约束实现。权限由 mask 和最终合成保证，数量需要对象/人工检查。不同模型的提示策略单独登记，不能给不支持 negative prompt 的后端强行传参并忽略错误。

### 17.4 给开发 Agent 的执行说明

先读仓库 CONTROL、P2 README、现有合同和本文；首个任务只做 P2-01 与 P2-02 的最小闭环。实现前提交未知尺度会话和蒙版语义 ADR，不修改 P1/P3 业务口径。

先验证原图坐标、不可变历史、授权合成，再接本地 SD1.5 分支。禁止直接复用 P1 整图 img2img 冒充蒙版重绘；禁止模型未运行就填写生成指标。每次提交保留测试和未完成项，用户图片只留私有工作区，公共测试用合成图。

## 18｜来源、核验范围与追溯

### 18.1 本仓库与用户输入

**[U01] 用户本轮上传平面图。** 私有对话文档包中的 `assets/source_plan.png` 为原字节副本；来源 SHA-256 见同一私有包的 `example_scope.json`。这些图片与 JSON 不随本次公共仓库同步。本轮仅添加选区说明素材，没有 AI 修改原图。

**[R01] AutoPlanDesign CONTROL.md（本轮读取 main）**  
https://github.com/yuancustom/AutoPlanDesign/blob/main/CONTROL.md  
用途：项目边界、本地部署、P2 记录、权限、几何失效及验收要求。

**[R02] P2 README**  
https://github.com/yuancustom/AutoPlanDesign/blob/main/projects/region-edit/README.md  
读取 blob：`1fe5c81e4755d96cc915789169743e15022b7354`。用途：确认 P2 仍为骨架。

**[R03] 当前 pipeline.schema.json**  
https://github.com/yuancustom/AutoPlanDesign/blob/main/contracts/pipeline.schema.json  
读取 blob：`b0c4df06a17cc533abfa980dec14a15c5d674fa3`。用途：发现未知尺度图片与现有强制米制矩阵合同的差异。

**[R04] 开发台账**  
https://github.com/yuancustom/AutoPlanDesign/blob/main/governance/backlog.json  
读取 blob：`4f34fce15202d8b49de3c1aca4c58bba7edad040`。用途：P2-01—05 任务映射。

**[R05] P1 冻结客户端**  
https://github.com/yuancustom/AutoPlanDesign/blob/main/projects/outline-plan/baseline/scripts/comfy_client.py  
读取 blob：`23bfc1b40d6485cc58159885141627a90ab812a3`。用途：确认旧管线没有输入局部编辑 mask。

### 18.2 开源应用和官方技术资料

**[S01] InvokeAI 官方仓库**  
https://github.com/invoke-ai/InvokeAI  
核验 Unified Canvas、Web UI、工作流和图库，未测试其在用户 Mac 的效果。

**[S02] Invoke 官方：Inpainting, Outpainting, and Bounding Box**  
https://support.invoke.ai/support/solutions/articles/151000096702-inpainting-outpainting-and-bounding-box  
核验候选暂存与 Accept 的交互说明。研究期间直接打开曾返回 502；相关交互由搜索返回的官方正文和 S01 交叉核对，未声称已操作软件。

**[S03] Krita AI Diffusion 官方仓库**  
https://github.com/Acly/krita-ai-diffusion  
核验选区填充、历史、控制层、ComfyUI 后端及本地路线；仓库列出的硬件支持不是本机性能保证。

**[S04] Krita AI Diffusion：Inpainting**  
https://github.com/Acly/krita-ai-diffusion/wiki/Inpainting  
核验 selection 与 context 的区别、上下文选取及其资源代价。

**[S05] ComfyUI：Mask Editor**  
https://docs.comfy.org/interface/maskeditor  
核验从 Load Image 打开画笔蒙版编辑器。

**[S06] ComfyUI：Routes**  
https://docs.comfy.org/development/comfyui-server/comms_routes  
核验本地 prompt、queue、history 和结果接口。业务幂等由 P2 另行实现。

**[S07] ComfyUI 官方 nodes.py**  
https://raw.githubusercontent.com/Comfy-Org/ComfyUI/master/nodes.py  
核验 VAEEncodeForInpaint、InpaintModelConditioning、LoadImage 等实现，不依赖第三方节点摘要推测。

**[S08] Konva：React Free Drawing**  
https://konvajs.org/docs/react/Free_Drawing.html  
核验笔画状态、画笔/擦除与可保存矢量交互。

**[S09] Konva：Relative Pointer Position**  
https://konvajs.org/docs/sandbox/Relative_Pointer_Position.html  
核验嵌套变换下的原图相对坐标映射。

**[S10] IOPaint 官方仓库**  
https://github.com/Sanster/IOPaint  
核验工具能力与 2025-08-13 归档声明，不作为持续维护承诺。

**[S11] ComfyUI-Inpaint-CropAndStitch 原作者仓库**  
https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch  
核验裁切/回贴、上下文、蒙版扩张、blur/fill holes 等参数；P2 不继承它们作为最终授权规则。

**[S12] Hugging Face Diffusers：Inpainting**  
https://huggingface.co/docs/diffusers/using-diffusers/inpaint  
核验白改黑保、专用重绘、未选区可能变化、overlay 与 crop 概念。网页 CUDA 示例不直接当 Mac 安装脚本。

**[S13] SD1.5 Inpainting 模型卡（镜像维护入口）**  
https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting  
用途：专用重绘候选与来源核对。

**[S14] SDXL Inpainting 模型卡**  
https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1  
用途：SDXL 专用重绘候选。

**[S15] ComfyUI 官方 nodes_mask.py**  
https://raw.githubusercontent.com/Comfy-Org/ComfyUI/master/comfy_extras/nodes_mask.py  
用途：显式 image-channel 转 mask 与蒙版操作。

**[S16] ComfyUI 官方 Differential Diffusion**  
https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_differential_diffusion.py  
用途：记录后续差异重绘实验；不声称硬锁几何。

**[S17] LaMa 原作者仓库**  
https://github.com/advimman/lama  
用途：消除/补洞基线，不当作文字指令对象生成模型。

**[S18] FLUX.2 klein 4B 官方模型卡**  
https://huggingface.co/black-forest-labs/FLUX.2-klein-4B  
用途：指令编辑候选、参数规模与硬件口径边界。

**[S19] Qwen2.5-VL-3B-Instruct 官方模型卡**  
https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct  
用途：可选视觉理解/意图辅助，与生图赛道分开。

**[S20] BrushNet 原作者仓库**  
https://github.com/TencentARC/BrushNet  
用途：后续专用重绘对比，不证明 MPS 兼容。

**[S21] PowerPaint 原作者仓库（重定向后的地址）**  
https://github.com/open-mmlab/PowerPaint  
用途：后续对象插入/移除方法对比，不证明用户机器实测。

---

**文档结论：先做一个能准确选区、严格限制写回、完整保存历史的编辑器，再用本机模型提升区内内容；几何与尺寸从不由图片效果代替。**
