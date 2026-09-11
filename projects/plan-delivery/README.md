# P3 · 已确认平面图到DXF / PDF / GLB

独立模块：autoplan_delivery。已找到用户完整Skill包；16个原文件冻结导入vendor；assets/project.schema.json、scripts/validate_project.py和scripts/validate_deliverables.py的写入被平台拦截，导入状态PARTIAL_BLOCKED。来源、19个预期hash及缺项见IMPORT.json；补齐前不验收完整集成。原包配套脚本是检查器，不是完整建模引擎；新包目前只报告能力边界。原检查脚本与Schema未完整导入，vendor的测试与执行命令暂不可运行；不将独立骨架测试成功当作Skill集成成功。

```bash
cd projects/plan-delivery
python -m pip install -e .
python -m autoplan_delivery --capabilities
python -m unittest discover -s tests -v
```

阅读 `vendor/floorplan-to-dxf-pdf-glb/SKILL.md` 后，从P3-01写输入适配。原Skill输入台账、参数来源、审批与共享几何规则保持不变；适配代码放src，不直接修改vendor。

图像+匹配几何路径优先；只有图片时重新识图/校准、获取层高与对齐证据。用户确认版本/几何不匹配或过期时停止。没有真实尺度不能伪造米制图纸。

建筑交付目录只能有DXF/PDF/GLB；测试日志和JSON留内部工作区。不能用效果图或简单拉伸代替门窗开洞、楼梯连接及同源三格式。参见CONTROL第6节。
