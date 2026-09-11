# 多层平面图转DXF / PDF / GLB：Skill V1.0

给能看图、读写文件及运行Python的Agent使用的工作流程包。识图和几何重建由Agent按Skill执行；随包脚本仅负责输入与文件检查，不是通用图像识别模型或一键建模程序。

**建筑成果默认只交三份：多层合图DXF、多页PDF、完整分层GLB。** 参数来源、假设、变更和验证说明收进PDF。Skill本身的Markdown、JSON模板、Python脚本是工具资源，不属于建筑成果。

## 包内文件

```text
floorplan-to-dxf-pdf-glb/
  SKILL.md                         主入口：触发条件、流程、决策、成果合同
  README.md                        使用说明
  TESTING.md                       实际测试记录与未覆盖范围
  references/
    01-input-and-evidence.md        必要输入、估算、假设和证据分级
    02-reconstruction.md            校尺、轮廓、墙体、门窗、楼梯和层间关系
    03-export-contract.md           单位、坐标、图层、PDF版式和GLB层级
    04-validation-and-delivery.md   检查矩阵及失败/未检查的表达
    05-h50x30-case.md               本次案例：已确认与暂定严格分开
    06-shared-geometry.md           共享建筑几何中间数据接口
    sources.md                     官方技术依据
  assets/
    intake-template.md             给用户填写的最小参数单
    project.template.json          空项目内部参数模板
    project.h50x30-draft.json       保留未决项的H形案例
    project.schema.json            JSON结构规范
  scripts/
    validate_project.py            参数和审批状态检查，标准库即可运行
    validate_deliverables.py       三格式文件级检查
    test_validators.py             24项回归测试，含合成文件读写测试
  requirements-validation.txt      文件检查的已测试直接依赖版本
  requirements-tests.txt           测试另需ReportLab和jsonschema
```

## 给另一个AI的启动指令

复制整段并附上实际楼层图纸：

```text
请读取并执行附件floorplan-to-dxf-pdf-glb中的SKILL.md。
根据我提供的各层平面图和已有参数，生成建筑方案级几何模型。
先读取资料，区分用户确认、图纸明示、计算推导、图像估算和建模假设。
只问资料中缺失且影响绝对尺度、层间关系或方案修改的关键问题。
轮廓差异、楼梯错位、新增走道或门位调整不得未经明确批准自行修改。
二维和三维都从同一份共享建筑几何生成，按Skill完成回读和视觉检查。
建筑成果只交DXF、PDF、GLB，参数/假设/变更/检查说明全部放入PDF。
不要交STEP、OBJ、HTML查看器、JSON、独立README或额外预览图片。
```

完整目录可放入目标Agent支持的Skill目录；安装位置随客户端而异，本包不执行安装、不声明已在任何客户端启用。只传主文件时会缺少详细参考、模板和检查脚本，优先交付整个目录。

## 执行目录

在Skill根目录下建`_work/`与`deliverables/`，把模板复制为`_work/project.json`。源文件路径默认相对这个JSON文件所在目录解析，不是相对当前命令目录；运行前填写实际路径。

输入检查只需Python 3.10及以上标准库：

```bash
python scripts/validate_project.py _work/project.json --check-source-paths --report _work/input_check.json
```

未提供源文件或关键参数时会返回2，这是正常阻断。脚本不会读取图片；`--check-source-paths`仅检查文件存在，不检查内容是否正确。

完整文件检查/测试依赖的组合要求Python 3.11及以上，建议使用独立环境。下列Conda环境名可自行修改，不要与同一目录的另一套venv混用：

```bash
conda create -n floorplan-skill python=3.11 -y
conda activate floorplan-skill
python -m pip install -r requirements-validation.txt
python scripts/validate_deliverables.py deliverables --report _work/output_check.json
```

以上环境创建和安装需要在运行端执行；本包没有修改用户设备。依赖安装需要相应软件源网络访问，检查脚本本身不上传文件或主动联网。已实际测试的环境记录见TESTING.md，不把版本锁定等同于所有操作系统都已验证。

构建阶段由Agent按`SKILL.md`和共享几何合同编写/调用适合图纸的建模代码。本包**没有**一个隐藏的`build.py`可以从模板直接产出真实建筑；不要捏造该命令。

运行检查脚本回归测试：

```bash
python -m pip install -r requirements-tests.txt
python -m unittest discover -s scripts -p 'test_*.py' -v
```

## 返回码与验收范围

- `0`：对应脚本实际实施的检查没有阻断错误，可能有WARN；不是完整建模验收或工程合规结论。
- `1`：执行环境/依赖/读取配置等异常。
- `2`：输入待补、决策未批、或交付文件不满足当前合同。

`validate_project.py`不是完整JSON Schema验证器，只实施文档说明的业务检查；`project.schema.json`另用于结构验证。`critical`标识参数风险，必填性由当前尺度方式、楼层高度等实际引用关系决定；未采用的总宽字段不会阻止通过一个可靠已知长度定尺度。

`validate_deliverables.py`没有包含跨格式对象几何比对、PDF实际打印比例、视觉复核或完整Khronos glTF Validator。Agent仍须执行这些适用检查，并逐项记录PASS/FAIL/WARN/NOT_RUN。

## 本次H形例子的保护行为

```bash
python scripts/validate_project.py assets/project.h50x30-draft.json
```

该示例预期返回2：层高含义采用了旧版解释，且统一H形、调整楼梯、新增走道均没有明确审批证据。示例中50×30米、4/3/3米是已给定数值，0/4/7/10米是在相应基准与高度含义下的推导。17/16/17米分段、4米凹口、墙厚、门窗和走道不能变成所有新项目的默认事实。

局部首层坐标原点取0是坐标约定，不是“用户批准了某个建筑标高”，示例使用`not_applicable`而不虚构审批。下一次项目从空模板开始，勿直接把H形例子的pending改成confirmed来消除报错。
