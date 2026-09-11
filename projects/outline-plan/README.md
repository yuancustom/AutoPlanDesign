# P1 · 带尺寸轮廓到初步平面图

独立模块：autoplan_outline。边界见根CONTROL第4节。本轮只建立新包骨架，并完整保留旧L形实现；不能把旧示意单位当成米制。

```bash
cd projects/outline-plan
python -m pip install -e .
python -m autoplan_outline --capabilities
python -m unittest discover -s tests -v
```

复现旧基线（安装在独立环境）：

```bash
cd baseline
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_pilot.py --mode geometry --out runs/l-shape-reference
```

baseline与原提交树完全一致，冻结不改。图纸输入、米制校准和通用排房在src新实现，不能只改名称/比例尺伪装完成。P1-01先校准和检查真实轮廓，再做功能程序与逐层生成。产出PlanRevision须带图像、几何和尺寸证据。

独立性验收：新项目测试不依赖P2/P3；未来接口包按版本安装，不import其内部路径。旧基线47项测试只是回归参照。模型原始输出、几何图、mock、dry-run分开保存。
