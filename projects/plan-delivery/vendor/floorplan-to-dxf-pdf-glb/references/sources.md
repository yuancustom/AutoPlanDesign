# 技术依据与范围

技术文档核对日期：2026-09-10。下列资料只支持Skill包装、单位、文件接口及验证机制，不为建筑方案的结构、消防或施工可用性背书。对依赖版本的描述应以实际运行记录为准。

[S1] Agent Skills官方格式规范：`SKILL.md`的YAML头、名称规则、可选scripts/references/assets及渐进加载。主文件采用这一目录约定，不包含产品专用安装路径或权限声明。

```text
https://agentskills.io/specification
```

[S2] ezdxf DXF Units：DXF几何数值和单位头分开，毫米INSUNITS=4；插入块单位变换需显式处理。

```text
https://ezdxf.readthedocs.io/en/stable/concepts/units.html
```

[S3] Khronos glTF 2.0 Specification：右手系、+Y向上、距离单位米、节点树、GLB存储、外部资源与材质定义。使用的建筑到glTF旋转是本Skill选定的导出约定。

```text
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
```

[S4] Trimesh glTF交换接口：`export_glb`、`load_glb`及基础schema检查接口。基础加载和schema检查不是完整语义或工程审查。

```text
https://trimesh.org/trimesh.exchange.gltf.html
```

[S5] ezdxf Drawing接口：文档读写及`audit()`。

```text
https://ezdxf.readthedocs.io/en/stable/drawing/drawing.html
```

[S6] PyMuPDF Page文档：`get_drawings`、`get_text`、`get_fonts`、`get_pixmap`等页面读取/渲染接口。统计不能代替视觉检查。

```text
https://pymupdf.readthedocs.io/en/latest/page.html
```

[S7] Khronos glTF Validator官方项目：完整glTF格式验证建议工具。本包的检查脚本没有集成或冒充该工具。

```text
https://github.com/KhronosGroup/glTF-Validator
```

案例来源：当前对话用户图片与参数；旧V01《建模假设与调整记录》。新项目必须重新获取实际输入，不能把案例图和假设当成通用建筑规范。
