---
name: outline-floorplan-local
description: 在用户指定建筑外轮廓内组织多楼层功能几何，校验来源、房间、门和跨层核心，逐层调用本地 ComfyUI，程序添加中文并合成一栋一图。用于机房、机柜、办公室、楼梯、厕所等辅助建筑概念方案，不提供施工或规范合规结论。
metadata:
  version: "1.1.1-main-pilot"
---

# 轮廓到三层布置 / AutoPlanDesign

工作目录是包含 AGENTS.md 的项目根目录。先读 README.md、docs/IMPLEMENTATION_REPORT.md、docs/PROVENANCE.md。

## 输入与边界

只试用户总览图的 02 L 形；输入是 `examples/source_crops/02.png`，它是原图浅蓝选区的二色表示，不是原始彩色截图。处理规则及原图哈希见同目录 PROVENANCE.json。

当前布局由 `scripts/l_shape_case.py` 明确编写并保存为 JSON，没有调用本地 LLM 或通用排房求解器。新轮廓需另提布局，不自动套这个预设。用户仅给一个外轮廓，本轮明确假设三层同边界，不发明退台、悬挑、真实尺寸或北向。

## 不可覆盖的约束

原轮廓与孔洞优先于名称和风格。各层同一坐标、方向、尺度，禁止独立缩放掩盖核心错位。房间与显式设备不能越界或重叠。楼梯、卫生间、管井的 core_id、类别与几何跨层固定；交通空间不允许 AI 重绘。所有门都必须位于所声明空间的共享边界。

一栋一图是最终交付单位；生成时单层串行，batch=1、concurrency=1。中文标签、楼层标题和说明由程序从 JSON 绘制，不让模型写字。生图时不同时驻留本地语言模型。

## 标准执行

1. 只读检查环境：`python scripts/doctor.py --out runs/doctor.json`。输出只证明执行它的机器状态，不能用 Linux 结果声称检查过 Mac。
2. 读取来源和任务要求；区分整栋必需功能与每层必需功能。将机房暂解释为辅助设备房，不设计主机组工艺。来源信息不清晰时停止。
3. 提出布局：锁定外壳，再确定跨层核心、公共走廊、主要空间、配套及门。以 `examples/l_shape_job.json` 为完整可运行样例，通过 `--job` 传入修改后的数据，不改源码硬编码后假装读取了新方案。
4. 几何检查：轮廓/房间合法、包含与重叠、逐层功能、门共享边界、门图连接、核心对齐和来源哈希。校验不通过不得进入生图，不能靠最终外壳裁切掩盖错误布局。
5. 几何试跑：`python scripts/run_pilot.py --mode geometry --job examples/l_shape_job.json --out runs/l-first`。查看 PNG、SVG 和 preview.html；状态只能到 geometry_passed。
6. 预演：新目录执行 `--mode dry-run`。只构造三个 API 工作流，不联网、不加载模型，不产生模型图。
7. 真实本地生成：配置 `configs/comfy_sd15.json`，再执行 `--mode render --ack-concept-only`。当前接口只支持 SD1.5 + 匹配 Canny ControlNet；不能只换文件名就认为支持 SDXL、FLUX 或 Z-Image。只访问本机 HTTP，不继承代理、不跟随重定向、不回退云端。
8. 原图复核：逐层检查 `generated/floor_N.png` 的假墙、假门、设备、交通与轮廓漂移，保留 prompt ID、参数及原图。ControlNet 是引导，不是硬几何锁定。后处理重描墙线和蒙版裁切不证明模型正确。
9. 中文拼版和概念验收：程序保留权威几何层，仅在允许区域使用模型像素。三层原图、中文与跨层核心均经人工检查后才能单独记录 concept_reviewed；脚本不自动签署该状态。

## 产物及失败处理

job.json 为权威三层数据；geometry_qa.json 与 source_audit.json 是程序几何证据，不是生成图评分。guides/ 内保存无字底图、Canny、快照及哈希；修改任一底图就应重做。workflows/ 仅用于 dry-run，generated/ 仅用于真实模型原图和执行记录。

board_geometry.png、overview_geometry.png、floor_N_geometry.svg 与 preview.html 都是程序结构图。board_model_unreviewed.png 是待审模型合成图；run_report.json 记录本次模式、平台、阶段和失败原因。

输出目录非空就停止，不覆盖旧结果。服务未启动、权重缺失、哈希变化、模型输出尺寸不一致均停止并留证据。不自动拉伸结果；超时后核查原 prompt ID，避免重复排队；不清除其他人的 ComfyUI 队列。缺少权重哈希、峰值内存或实测耗时就如实留空。

## 概念与工程边界

1F 辅助运行，2F 控制通信与技术办公，3F 办公会议和保障。双楼梯只是示例，不是消防数量结论。单纯门图连通不证明人可安全通行。楼梯踏步/平台/净高、疏散距离与净宽、门扇冲突、检修净距、荷载、湿区排水、电气防火、主工艺均需专业审查。

## 仓库操作

目标 `yuancustom/AutoPlanDesign`。用户已明确授权直接向 main 提交，其他分支已清理。更新前读取最新 main，使用普通增量提交并保留历史，不 force push，不创建新分支/PR，除非用户修改要求。创建 tree 或 commit 对象不等于发布完成；必须更新 main 并回读分支头与文件才能报告成功。
