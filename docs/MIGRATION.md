# 本次仓库重整

旧main提交：`9be671d75484f497f474aa5b8df23a0a02d429ad`；旧根树：`996e1da2ede618f7f62610d05eec6983d5f89961`。

## 迁移而非破坏历史

根目录旧实现整体移到 `projects/outline-plan/baseline/`，使用同一个Git tree引用，因此源码、示例及原有证据字节不变。该目录是冻结参考；内部README/Skill/AGENTS描述旧项目，不是新总控。旧CI放进该目录后不会自动触发；新的根CI显式进入baseline运行其测试。

根入口换为CONTROL、三项目、contracts、benchmarks、agent、governance和新CI。未清空Git历史、未force-push、未创建新分支/PR；本次提交以旧main为父提交。恢复旧内容可用旧commit按路径读取，不需要重写分支历史。

## P3来源

用户Library完整包 `floorplan-to-dxf-pdf-glb-skill-v1.0.zip`（SHA-256 `3ad9028c17f40c24222515966b5822d151db560956822e68054dd5eacd52ba9f`）已将允许的16个原文件导入P3/vendor；assets/project.schema.json、scripts/validate_project.py、scripts/validate_deliverables.py写入被平台拦截，未重试或绕过。IMPORT.json记录19个原文件的预期hash和3项明确阻塞，状态PARTIAL_BLOCKED。没有打包字体或模型权重。模板H50×30是待决样例，不是所有项目默认参数。

## 兼容

旧命令从P1/baseline目录运行。旧diagram_units不自动转换为米制。旧PNG不是新P1有尺寸金标准，也不是P2/P3模型测试结果。

当前新包只有独立能力探测接口；不提供兼容假生图入口。依赖冻结、模型适配和历史数据迁移由任务台账跟踪。
