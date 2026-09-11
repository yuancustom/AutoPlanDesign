# 跨项目数据合同 · 0.1.0（规划基线）

入口文件为 `pipeline.schema.json`，使用 JSON Schema Draft 2020-12。Schema只验证结构；闭合、自交、单位转换、可达性、蒙版定位、哈希内容匹配、真实授权等必须由业务校验器实现。不能因 JSON 合法就写 geometry_passed。

## 接口

- P1：`generate(FootprintSpec, ProgramSpec) -> PlanRevision[]`。输入同时支持世界坐标轮廓和已校准图像；尺度缺失返回NEEDS_INPUT。当前schema fixture侧重世界坐标入口，扫描件校准另行扩展。
- P2：`edit(PlanRevision, EditRequest) -> EditAttempt`，`accept(candidate, ApprovalEvent) -> PlanRevision`。请求绑定base revision及expected head，不能覆盖原版。
- P3：`reconstruct(ApprovedPlanSet, ReconstructionSpec) -> BuildingIR`；`export(BuildingIR) -> ExportManifest`。不能从STALE几何导出。
- Agent：仅调用这些公开接口；返回状态/错误不等于业务成功。Schema文件作为版本化制品，未来发布独立contracts包，不通过跨项目相对路径import。

## 不丢失的信息

PlanRevision含图片与几何引用/hash、楼层稳定ID、事实与来源、变换、批准事件、父版本。原图像素坐标u右/v下；建筑x/y平面、z上，米单位。任何分层图板裁切需记录panel变换，禁止把不同楼层图当同一张图统一拉伸。

EditRequest区分input canvas、context mask和effective edit mask；context是供模型观察的区域，不扩大修改授权。保留brush矢量笔画及原分辨率掩膜，客户端缩放/设备像素比只用于显示。

BuildingIR应扩展floor/wall/opening/room/stair/slab/equipment的稳定ID、宿主关系、几何、证据ID；三格式由同一IR和revision导出。细节遵守 P3/vendor 原始 Skill 的 `references/06-shared-geometry.md`，不得发明第二套冲突合同。

## 失效规则

plan image 或 layout 版本变化→geometry需要匹配或标STALE；任一受影响楼层过期→building reconstruction/export过期。appearance-only也须原始图复核。approved事件必须匹配被确认的版本/hash；复制批准字段不会继承旧授权。

## Schema 的当前覆盖范围

当前覆盖FootprintSpec、PlanRevision、EditRequest、BenchmarkRun最小字段与语义边界；BuildingIR/ExportManifest完整schema与跨格式验证列入GOV-02/P3任务。fixtures全部合成，只验证接口，不是已运行的模型结果。v0.1允许在M1前修订；破坏性修改升minor版本并更新消费方，v1以后破坏性修改升major。
